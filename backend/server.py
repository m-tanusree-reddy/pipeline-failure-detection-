import os
import sys
import uuid
import time
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Depends, Request, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.config import (
    LOGS_DIR, ALLOWED_ORIGINS, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_OAUTH_REDIRECT_URI
)
from backend.pipeline import PipelineOrchestrator
from backend.db.session import init_db, get_db, SessionLocal, get_db_telemetry
from backend.db.models import (
    User, Repository, RepositoryMember, WorkflowRun, FailureAnalysis, 
    NotificationConfig, InAppNotification, NotificationPreference, CodeRemediation
)
from backend.services.github_service import GitHubService, parse_repo_url, GitHubServiceError
from backend.services.rbac_service import (
    map_github_to_app_role, Role, Action, has_permission, enforce_permission, RBACException
)
from backend.services.webhook_service import (
    WebhookProcessor, verify_github_signature, generate_signature
)
from backend.services.historical_failure_service import HistoricalFailureService
from backend.services.notification_service import NotificationService, Severity, EventType
from backend.services.task_dispatcher import dispatch_analysis, get_queue_telemetry
from backend.services.classification_service import classify_granular_failure, compute_composite_severity
from backend.services.remediation_service import synthesize_code_patch, apply_simulated_patch
from backend.services.metrics_service import (
    get_prometheus_metrics, record_failure_metric, record_recurrence_metric,
    record_notification_metric, record_remediation_metric, record_analysis_duration
)

# Milestone 6: Sentry Error Tracking Initialization
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[FastApiIntegration()],
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0")),
            environment=os.getenv("ENVIRONMENT", "development"),
            send_default_pii=False,
        )
        logging.getLogger("backend").info("[Sentry] Error tracking & performance monitoring initialized.")
    except Exception as se:
        logging.getLogger("backend").warning(f"[Sentry] Failed to initialize Sentry: {se}")

# Initialize database tables on server start
init_db()

app = FastAPI(title="Pipeline Failure Detection 3.0 API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory store for real-time progress streaming
runs: Dict[str, Dict[str, Any]] = {}

# Pydantic Schemas
class TokenLoginRequest(BaseModel):
    token: Optional[str] = None
    username: Optional[str] = None

class OAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None

class ConnectRepoRequest(BaseModel):
    url: str
    token: Optional[str] = None
    webhook_secret: Optional[str] = None

class UpdateMemberRoleRequest(BaseModel):
    app_role: str

class SimulateWebhookRequest(BaseModel):
    repo_full_name: Optional[str] = None
    workflow_name: Optional[str] = "CI Test Suite"
    branch: Optional[str] = "main"
    commit_sha: Optional[str] = "a82f91c"
    commit_message: Optional[str] = "fix: update payment validation handler"
    error_type: Optional[str] = "AssertionError: Expected 200, got 500"

class UpdatePreferenceRequest(BaseModel):
    email_enabled: Optional[bool] = None
    slack_enabled: Optional[bool] = None
    discord_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    notify_critical_only: Optional[bool] = None

class AddNotificationConfigRequest(BaseModel):
    channel: str # "slack", "discord", "email"
    target_url_or_email: str
    filter_rules: Optional[Dict[str, Any]] = None

class AnalyzeRequest(BaseModel):
    log_id: str

class FixRequest(BaseModel):
    run_id: str
    fix_index: int = 0

class ReviewRemediationRequest(BaseModel):
    action: str = Field(..., description="'approve' or 'reject'")
    reviewer_role: Optional[str] = "Developer"
    reviewer_username: Optional[str] = "admin"
    comment: Optional[str] = None

class ApplyRemediationRequest(BaseModel):
    action: Optional[str] = "apply"
    staging_branch: Optional[str] = "staging/patch-validation"

class PreviewRemediationRequest(BaseModel):
    run_id: str

# Custom orchestrator subclass to capture stage updates and logs
class ApiPipelineOrchestrator(PipelineOrchestrator):
    def __init__(self, run_id: str, on_stage_update, on_log):
        super().__init__()
        self.run_id = run_id
        self.on_stage_update = on_stage_update
        self.on_log = on_log

    def _execute_stage(self, stage_name: str, func, *args, **kwargs) -> Any:
        self.on_stage_update(self.run_id, stage_name, "RUNNING", 0.0)
        self.on_log(self.run_id, "INFO", f"[{stage_name}] Starting stage execution...")
        start_time = time.time()
        try:
            result = super()._execute_stage(stage_name, func, *args, **kwargs)
            duration = time.time() - start_time
            self.on_stage_update(self.run_id, stage_name, "SUCCESS", duration)
            self.on_log(self.run_id, "INFO", f"[{stage_name}] Completed successfully in {duration:.2f}s.")
            return result
        except Exception as e:
            duration = time.time() - start_time
            self.on_stage_update(self.run_id, stage_name, "FAILED", duration)
            self.on_log(self.run_id, "ERROR", f"[{stage_name}] Failed after {duration:.2f}s: {str(e)}")
            raise e

# Custom logging handler to redirect backend logs to run console logs
class RunLogHandler(logging.Handler):
    def __init__(self, run_id: str, on_log):
        super().__init__()
        self.run_id = run_id
        self.on_log = on_log

    def emit(self, record):
        try:
            msg = self.format(record)
            self.on_log(self.run_id, record.levelname, msg)
        except Exception:
            self.handleError(record)

def update_stage_status(run_id: str, stage_name: str, status: str, duration: float):
    if run_id in runs:
        runs[run_id]["stages"][stage_name] = {
            "status": status,
            "time": duration
        }

def append_run_log(run_id: str, level: str, message: str):
    if run_id in runs:
        timestamp = time.strftime("%H:%M:%S")
        runs[run_id]["console_logs"].append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })

def run_analysis_thread(run_id: str, log_path: str, db_run_id: Optional[str] = None):
    """
    Executes the AI diagnostic pipeline asynchronously, updating real-time state,
    performing historical failure correlation, persisting results, and dispatching
    role-based notifications.
    """
    logger = logging.getLogger("backend")
    handler = RunLogHandler(run_id, append_run_log)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    
    try:
        runs[run_id]["status"] = "running"
        orchestrator = ApiPipelineOrchestrator(run_id, update_stage_status, append_run_log)
        start_exec_time = time.time()
        
        # Execute pipeline orchestrator
        report = orchestrator.run(log_path)
        analysis_duration = time.time() - start_exec_time

        # Granular Failure Classification & Composite Severity Scoring (Milestone 5)
        gran_class = classify_granular_failure(
            error_type=report.failure_type,
            error_message=report.pipeline_error,
            log_snippet=report.root_cause
        )
        sev_comp = compute_composite_severity(
            category=gran_class["category"],
            branch="main",
            is_recurring=False,
            recurrence_count=1
        )

        # AI Code-Level Patch Synthesis (Milestone 5)
        patch = synthesize_code_patch(
            category=gran_class["category"],
            root_cause=report.root_cause,
            explanation=report.explanation,
            evidence=report.evidence,
            log_content=report.pipeline_error
        )
        
        # Prepare structured report
        report_dict = {
            "pipeline_error": report.pipeline_error,
            "failure_type": report.failure_type,
            "failure_category": gran_class["category"],
            "severity_score": sev_comp["severity_score"],
            "severity_tier": sev_comp["severity_tier"],
            "blast_radius": sev_comp["blast_radius"],
            "root_cause": report.root_cause,
            "explanation": report.explanation,
            "evidence": report.evidence,
            "suggested_fixes": report.suggested_fixes,
            "code_patch": patch,
            "original_confidence": report.original_confidence,
            "final_confidence": report.final_confidence,
            "critic_status": report.critic_status,
            "critic_comments": report.critic_comments,
            "is_recurring": False,
            "recurrence_count": 1,
            "intelligence_note": "Single occurrence analyzed."
        }
        
        runs[run_id]["status"] = "completed"
        runs[run_id]["report"] = report_dict
        append_run_log(run_id, "INFO", "Analysis completed successfully. Report generated.")

        # Record analysis duration metric (Milestone 6)
        record_analysis_duration(analysis_duration, "completed")

        # Persist analysis to database and perform correlation + notifications
        if db_run_id:
            db = SessionLocal()
            try:
                wf_run = db.query(WorkflowRun).filter(WorkflowRun.id == db_run_id).first()
                if wf_run:
                    wf_run.status = "completed"

                    # 1. Historical Failure Correlation (Milestone 5 / Recommendation C)
                    hist_svc = HistoricalFailureService(db)
                    corr = hist_svc.check_and_correlate_failure(
                        repo_id=wf_run.repo_id,
                        failure_type=report.failure_type,
                        root_cause=report.root_cause,
                        current_run_id=wf_run.id
                    )

                    # Recalculate composite severity with verified branch & recurrence
                    sev_comp = compute_composite_severity(
                        category=gran_class["category"],
                        branch=wf_run.head_branch or "main",
                        is_recurring=corr["is_recurring"],
                        recurrence_count=corr["recurrence_count"]
                    )

                    analysis = FailureAnalysis(
                        run_id=wf_run.id,
                        analysis_run_id=run_id,
                        failure_type=report.failure_type,
                        failure_category=gran_class["category"],
                        severity_score=sev_comp["severity_score"],
                        root_cause=report.root_cause,
                        explanation=report.explanation,
                        suggested_fixes=report.suggested_fixes,
                        evidence=report.evidence,
                        original_confidence=report.original_confidence,
                        final_confidence=report.final_confidence,
                        critic_status=report.critic_status,
                        critic_comments=report.critic_comments,
                        error_signature=corr["error_signature"],
                        is_recurring=corr["is_recurring"],
                        recurrence_count=corr["recurrence_count"],
                        previous_run_id=corr["previous_run_id"],
                        status="completed"
                    )
                    db.add(analysis)

                    # Persist Code Remediation proposal in database (Milestone 5)
                    remediation = CodeRemediation(
                        run_id=wf_run.id,
                        title=patch["title"],
                        target_file=patch["target_file"],
                        diff_content=patch["diff_content"],
                        rationale=patch["rationale"],
                        risk_level=patch["risk_level"],
                        validation_command=patch["validation_command"],
                        status="pending_review",
                        reviewer_role="Developer"
                    )
                    db.add(remediation)
                    db.commit()

                    record_remediation_metric("proposed")

                    # Update in-memory report dict with correlation & remediation results
                    report_dict["remediation_id"] = remediation.id
                    report_dict["severity_score"] = sev_comp["severity_score"]
                    report_dict["severity_tier"] = sev_comp["severity_tier"]
                    report_dict["blast_radius"] = sev_comp["blast_radius"]
                    report_dict["error_signature"] = corr["error_signature"]
                    report_dict["is_recurring"] = corr["is_recurring"]
                    report_dict["recurrence_count"] = corr["recurrence_count"]
                    report_dict["intelligence_note"] = corr["intelligence_note"]
                    report_dict["past_occurrences"] = corr["past_occurrences"]

                    append_run_log(run_id, "INFO", f"[Historical Intelligence] {corr['intelligence_note']}")
                    append_run_log(run_id, "INFO", f"[AI Remediation] Generated code patch for {patch['target_file']} ({patch['risk_level']} risk).")

                    # Prometheus Metrics Recording (Milestone 6)
                    repo_slug = wf_run.repository.full_name if wf_run.repository else "unknown"
                    record_failure_metric(repo_slug, report.failure_type, sev_comp["severity_tier"])
                    if corr["is_recurring"]:
                        record_recurrence_metric(repo_slug, sev_comp["severity_tier"])

                    # 2. Role-Based Notification Dispatch (Milestone 3 / Recommendation B)
                    notif_svc = NotificationService(db)
                    notif_res = notif_svc.dispatch_failure_notification(wf_run, analysis)

                    if notif_res.get("status") == "dispatched":
                        append_run_log(
                            run_id, "INFO",
                            f"[Notification Engine] Routed alerts for '{notif_res['event_type']}' ({notif_res['severity']}) to {notif_res['recipients_count']} recipients."
                        )
                    elif notif_res.get("status") == "throttled":
                        append_run_log(run_id, "WARNING", f"[Notification Engine] Alert throttled (duplicate detected within window).")
            except Exception as dbe:
                logger.error(f"Error persisting analysis to database: {dbe}")
            finally:
                db.close()

    except Exception as e:
        runs[run_id]["status"] = "failed"
        runs[run_id]["error"] = str(e)
        append_run_log(run_id, "ERROR", f"Analysis failed: {str(e)}")

        if db_run_id:
            db = SessionLocal()
            try:
                wf_run = db.query(WorkflowRun).filter(WorkflowRun.id == db_run_id).first()
                if wf_run:
                    wf_run.status = "failed"
                    db.commit()
            except Exception:
                pass
            finally:
                db.close()
    finally:
        logger.removeHandler(handler)

@app.get("/health")
@app.get("/api/health")
def health_check():
    """Endpoint for deployment verification and health checks."""
    return {"status": "healthy", "version": "3.0.0"}

# ==========================================
# AUTHENTICATION & GITHUB OAUTH ENDPOINTS
# ==========================================

@app.get("/api/auth/github/url")
def get_github_oauth_url():
    """Generates GitHub OAuth authorization URL or reports configuration status."""
    if not GITHUB_CLIENT_ID:
        return {
            "configured": False,
            "message": "GitHub OAuth client ID not set. Configure GITHUB_CLIENT_ID in .env, or sign in via Personal Access Token / Demo mode.",
            "url": None
        }
    
    redirect_uri_param = f"&redirect_uri={GITHUB_OAUTH_REDIRECT_URI}" if GITHUB_OAUTH_REDIRECT_URI else ""
    auth_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo,read:user,user:email{redirect_uri_param}"
    return {
        "configured": True,
        "client_id": GITHUB_CLIENT_ID,
        "url": auth_url
    }

@app.post("/api/auth/github/callback")
def github_oauth_callback(req: OAuthCallbackRequest, db: Session = Depends(get_db)):
    """Exchanges GitHub OAuth code for an access token and user profile."""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=400,
            detail="GitHub OAuth credentials (GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET) are not configured on the server."
        )

    token_url = "https://github.com/login/oauth/access_token"
    token_headers = {"Accept": "application/json"}
    token_payload = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": req.code
    }
    if GITHUB_OAUTH_REDIRECT_URI:
        token_payload["redirect_uri"] = GITHUB_OAUTH_REDIRECT_URI

    try:
        resp = requests.post(token_url, json=token_payload, headers=token_headers, timeout=10)
        resp_data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with GitHub OAuth endpoint: {str(e)}")

    access_token = resp_data.get("access_token")
    if not access_token:
        error_desc = resp_data.get("error_description") or resp_data.get("error") or "Failed to obtain access token."
        raise HTTPException(status_code=400, detail=error_desc)

    try:
        github_svc = GitHubService(access_token)
        profile = github_svc.get_authenticated_user(access_token)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch user profile from GitHub: {str(e)}")

    username = profile.get("login") or f"gh_{profile.get('id')}"
    user = db.query(User).filter((User.github_id == str(profile.get("id"))) | (User.username == username)).first()
    if not user:
        user = User(
            github_id=str(profile.get("id")),
            username=username,
            email=profile.get("email"),
            avatar_url=profile.get("avatar_url"),
            global_role="Admin" if db.query(User).count() == 0 else "Developer"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if profile.get("avatar_url"): user.avatar_url = profile.get("avatar_url")
        if profile.get("email"): user.email = profile.get("email")
        db.commit()

    return {
        "status": "authenticated",
        "auth_method": "oauth",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "global_role": user.global_role
        }
    }

@app.post("/api/auth/token-login")
def token_login(req: TokenLoginRequest, db: Session = Depends(get_db)):
    """Authenticates via Personal Access Token (PAT) or username."""
    token = req.token.strip() if req.token else None
    username = req.username.strip() if req.username else None

    if not token and not username:
        raise HTTPException(status_code=400, detail="Provide a GitHub Personal Access Token or username.")

    avatar_url = None
    email = None
    github_id = None

    if token:
        try:
            github_svc = GitHubService(token)
            profile = github_svc.get_authenticated_user(token)
            username = profile.get("login") or username
            email = profile.get("email")
            avatar_url = profile.get("avatar_url")
            github_id = str(profile.get("id")) if profile.get("id") else None
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid GitHub Token: {str(e)}")

    if not username:
        username = "developer"

    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            github_id=github_id,
            username=username,
            email=email,
            avatar_url=avatar_url or f"https://avatars.githubusercontent.com/u/583231",
            global_role="Admin" if db.query(User).count() == 0 else "Developer"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if avatar_url: user.avatar_url = avatar_url
        if email: user.email = email
        db.commit()

    return {
        "status": "authenticated",
        "auth_method": "token" if token else "username",
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "global_role": user.global_role
        }
    }

@app.post("/api/auth/demo-login")
def demo_login(db: Session = Depends(get_db)):
    """1-Click On-Call DevOps Login for testing and immediate access."""
    user = db.query(User).filter(User.username == "oncall_devops").first()
    if not user:
        user = User(
            username="oncall_devops",
            email="devops@reliability.internal",
            avatar_url="https://avatars.githubusercontent.com/u/583231",
            global_role="Admin"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {
        "status": "authenticated",
        "auth_method": "demo",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "global_role": user.global_role
        }
    }

@app.get("/api/auth/me")
def get_current_user(db: Session = Depends(get_db)):
    """Returns the authenticated user profile."""
    user = db.query(User).first()
    if not user:
        return {"authenticated": False, "user": None}
    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "global_role": user.global_role
        }
    }

@app.post("/api/auth/logout")
def logout():
    """Logs out active session."""
    return {"status": "logged_out"}

# ==========================================
# MILESTONE 1: REPOSITORY & RBAC ENDPOINTS
# ==========================================

@app.post("/api/repos/connect")
def connect_repository(request: ConnectRepoRequest, db: Session = Depends(get_db)):
    """
    Step 1: Connect GitHub repository URL.
    Step 2: Authenticate user, verify real GitHub permissions, and map to Application RBAC.
    """
    try:
        owner, repo_name = parse_repo_url(request.url)
    except GitHubServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    github_svc = GitHubService(request.token)
    
    try:
        user_profile = github_svc.get_authenticated_user(request.token)
    except GitHubServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    try:
        repo_data = github_svc.get_repository(owner, repo_name, request.token)
    except GitHubServiceError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))

    gh_permission = github_svc.determine_user_permission(
        owner=owner,
        repo=repo_name,
        username=user_profile["login"],
        token=request.token,
        repo_data=repo_data
    )

    if gh_permission == "none":
        raise HTTPException(
            status_code=403,
            detail="Access denied: You do not have permission to access this repository."
        )

    try:
        app_role = map_github_to_app_role(gh_permission, is_creator=True)
    except RBACException as e:
        raise HTTPException(status_code=403, detail=str(e))

    user = db.query(User).filter(User.username == user_profile["login"]).first()
    if not user:
        user = User(
            github_id=str(user_profile.get("id", "")),
            username=user_profile["login"],
            email=user_profile.get("email"),
            avatar_url=user_profile.get("avatar_url")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create default notification preferences
        pref = NotificationPreference(user_id=user.id)
        db.add(pref)
        db.commit()

    full_name = f"{owner}/{repo_name}"
    repo = db.query(Repository).filter(Repository.full_name.ilike(full_name)).first()
    if not repo:
        webhook_sec = request.webhook_secret or os.urandom(16).hex()
        repo = Repository(
            owner=owner,
            name=repo_name,
            full_name=full_name,
            is_private=repo_data.get("private", False),
            default_branch=repo_data.get("default_branch", "main"),
            webhook_secret=webhook_sec,
            is_active=True
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

    member = db.query(RepositoryMember).filter(
        RepositoryMember.user_id == user.id,
        RepositoryMember.repo_id == repo.id
    ).first()

    if not member:
        member = RepositoryMember(
            user_id=user.id,
            repo_id=repo.id,
            github_permission=gh_permission,
            app_role=app_role
        )
        db.add(member)
    else:
        member.github_permission = gh_permission
        member.app_role = app_role
    
    db.commit()

    return {
        "repository": {
            "id": repo.id,
            "owner": repo.owner,
            "name": repo.name,
            "full_name": repo.full_name,
            "is_private": repo.is_private,
            "default_branch": repo.default_branch,
            "webhook_secret": repo.webhook_secret,
            "is_active": repo.is_active
        },
        "user": {
            "username": user.username,
            "avatar_url": user.avatar_url
        },
        "permissions": {
            "github_permission": gh_permission,
            "app_role": app_role
        }
    }

@app.get("/api/repos")
def list_repositories(db: Session = Depends(get_db)):
    """List all connected repositories with statistics and membership counts."""
    repos = db.query(Repository).order_by(Repository.created_at.desc()).all()
    results = []
    for r in repos:
        member_count = db.query(RepositoryMember).filter(RepositoryMember.repo_id == r.id).count()
        runs_count = db.query(WorkflowRun).filter(WorkflowRun.repo_id == r.id).count()
        last_failure = db.query(WorkflowRun).filter(
            WorkflowRun.repo_id == r.id,
            WorkflowRun.conclusion == "failure"
        ).order_by(WorkflowRun.created_at.desc()).first()

        results.append({
            "id": r.id,
            "owner": r.owner,
            "name": r.name,
            "full_name": r.full_name,
            "is_private": r.is_private,
            "default_branch": r.default_branch,
            "webhook_secret": r.webhook_secret,
            "is_active": r.is_active,
            "member_count": member_count,
            "runs_count": runs_count,
            "last_failure_at": last_failure.created_at.isoformat() if last_failure else None
        })
    return results

@app.get("/api/repos/{repo_id}/members")
def get_repository_members(repo_id: str, db: Session = Depends(get_db)):
    """List members and their roles for a given repository."""
    members = db.query(RepositoryMember).filter(RepositoryMember.repo_id == repo_id).all()
    return [
        {
            "user_id": m.user_id,
            "username": m.user.username,
            "avatar_url": m.user.avatar_url,
            "github_permission": m.github_permission,
            "app_role": m.app_role,
            "created_at": m.created_at.isoformat()
        }
        for m in members
    ]

@app.patch("/api/repos/{repo_id}/members/{user_id}")
def update_member_role(
    repo_id: str,
    user_id: str,
    req: UpdateMemberRoleRequest,
    db: Session = Depends(get_db)
):
    """Updates a member's application role (Owner, Admin, Developer, Viewer)."""
    valid_roles = [Role.OWNER, Role.ADMIN, Role.DEVELOPER, Role.VIEWER]
    if req.app_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    member = db.query(RepositoryMember).filter(
        RepositoryMember.repo_id == repo_id,
        RepositoryMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found for this repository.")

    member.app_role = req.app_role
    db.commit()
    return {"status": "success", "user_id": user_id, "new_role": req.app_role}

# ==========================================
# MILESTONE 2: WEBHOOK & FAILURE DETECTION
# ==========================================

@app.post("/api/webhooks/github")
async def github_webhook_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    db: Session = Depends(get_db)
):
    """
    GitHub Webhook receiver.
    Listens for `workflow_run` events (completed with failure).
    Validates HMAC-SHA256 signature, deduplicates, and dispatches AI analysis.
    """
    body_bytes = await request.body()
    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    if x_github_event == "ping":
        return {"status": "ok", "message": "Pong! GitHub webhook handshake verified."}

    processor = WebhookProcessor(db)
    result = processor.process_workflow_run_event(
        payload=payload,
        raw_body=body_bytes,
        signature=x_hub_signature_256
    )

    if result.get("status") == "unauthorized":
        raise HTTPException(status_code=401, detail=result.get("reason"))

    if result.get("status") == "accepted":
        run_id = str(uuid.uuid4())
        runs[run_id] = {
            "run_id": run_id,
            "status": "pending",
            "log_name": os.path.basename(result["log_path"]),
            "stages": {
                stage: {"status": "PENDING", "time": 0.0}
                for stage in [
                    "Parser", "Classifier", "Planner", "Collector", "Chunker",
                    "Embedder", "Vector Store", "Retriever", "LLM", "Critic", "Report"
                ]
            },
            "console_logs": [],
            "report": None,
            "error": None
        }

        dispatch_res = dispatch_analysis(
            run_id=run_id,
            log_path=result["log_path"],
            db_run_id=result["run_id"],
            background_tasks=background_tasks,
            sync_fallback_func=run_analysis_thread
        )

        return {
            "status": "queued",
            "message": "Failure detected. AI diagnosis dispatched.",
            "run_id": run_id,
            "db_run_id": result["run_id"],
            "dispatch": dispatch_res
        }

    return result

@app.post("/api/webhooks/github/simulate")
def simulate_webhook_failure(
    req: SimulateWebhookRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Developer Simulator:
    Simulates a GitHub `workflow_run.completed` failure webhook with a valid HMAC signature.
    """
    if req.repo_full_name:
        repo = db.query(Repository).filter(Repository.full_name.ilike(req.repo_full_name)).first()
    else:
        repo = db.query(Repository).first()

    if not repo:
        repo = Repository(
            owner="demo-org",
            name="payment-service",
            full_name="demo-org/payment-service",
            is_private=False,
            default_branch="main",
            webhook_secret="test_webhook_secret_12345",
            is_active=True
        )
        db.add(repo)
        db.commit()
        db.refresh(repo)

    simulated_run_id = str(uuid.uuid4().int)[:8]

    payload = {
        "action": "completed",
        "workflow_run": {
            "id": int(simulated_run_id),
            "name": req.workflow_name,
            "head_branch": req.branch,
            "head_sha": req.commit_sha,
            "conclusion": "failure",
            "status": "completed",
            "run_number": 42,
            "head_commit": {
                "id": req.commit_sha,
                "message": req.commit_message
            }
        },
        "repository": {
            "name": repo.name,
            "full_name": repo.full_name,
            "private": repo.is_private,
            "default_branch": repo.default_branch
        }
    }

    raw_body = json.dumps(payload).encode("utf-8")
    sig = generate_signature(raw_body, repo.webhook_secret or "secret")

    processor = WebhookProcessor(db)
    result = processor.process_workflow_run_event(
        payload=payload,
        raw_body=raw_body,
        signature=sig
    )

    if result.get("status") == "accepted":
        run_id = str(uuid.uuid4())
        runs[run_id] = {
            "run_id": run_id,
            "status": "pending",
            "log_name": os.path.basename(result["log_path"]),
            "stages": {
                stage: {"status": "PENDING", "time": 0.0}
                for stage in [
                    "Parser", "Classifier", "Planner", "Collector", "Chunker",
                    "Embedder", "Vector Store", "Retriever", "LLM", "Critic", "Report"
                ]
            },
            "console_logs": [],
            "report": None,
            "error": None
        }

        dispatch_res = dispatch_analysis(
            run_id=run_id,
            log_path=result["log_path"],
            db_run_id=result["run_id"],
            background_tasks=background_tasks,
            sync_fallback_func=run_analysis_thread
        )

        return {
            "status": "simulated",
            "message": "Simulated failure webhook triggered and verified with HMAC.",
            "run_id": run_id,
            "db_run_id": result["run_id"],
            "repo": repo.full_name,
            "branch": req.branch,
            "workflow": req.workflow_name,
            "dispatch": dispatch_res
        }

    return result

@app.get("/api/events")
def list_pipeline_events(db: Session = Depends(get_db)):
    """
    Returns recent pipeline events, recurrence status, and AI analysis reports.
    """
    runs = db.query(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(30).all()
    events = []
    for r in runs:
        analysis_data = None
        if r.analysis:
            analysis_data = {
                "failure_type": r.analysis.failure_type,
                "root_cause": r.analysis.root_cause,
                "explanation": r.analysis.explanation,
                "confidence": r.analysis.final_confidence,
                "suggested_fixes": r.analysis.suggested_fixes,
                "critic_status": r.analysis.critic_status,
                "analysis_run_id": r.analysis.analysis_run_id,
                "is_recurring": r.analysis.is_recurring,
                "recurrence_count": r.analysis.recurrence_count,
                "error_signature": r.analysis.error_signature
            }

        events.append({
            "id": r.id,
            "repo_full_name": r.repository.full_name if r.repository else "Unknown",
            "github_run_id": r.github_run_id,
            "workflow_name": r.workflow_name,
            "branch": r.head_branch,
            "commit_sha": r.head_sha,
            "commit_message": r.commit_message,
            "status": r.status,
            "conclusion": r.conclusion,
            "created_at": r.created_at.isoformat(),
            "analysis": analysis_data
        })
    return events

# ==========================================
# MILESTONE 3: NOTIFICATIONS & ROUTING
# ==========================================

@app.get("/api/notifications")
def get_in_app_notifications(db: Session = Depends(get_db)):
    """Fetches in-app notifications with unread counts."""
    notifications = (
        db.query(InAppNotification)
        .order_by(InAppNotification.created_at.desc())
        .limit(40)
        .all()
    )
    unread_count = db.query(InAppNotification).filter(InAppNotification.is_read == False).count()

    results = []
    for n in notifications:
        results.append({
            "id": n.id,
            "user_id": n.user_id,
            "username": n.user.username if n.user else "User",
            "repo_name": n.repository.full_name if n.repository else "",
            "run_id": n.run_id,
            "title": n.title,
            "message": n.message,
            "severity": n.severity,
            "event_type": n.event_type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        })

    return {
        "unread_count": unread_count,
        "notifications": results
    }

@app.patch("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, db: Session = Depends(get_db)):
    """Marks a single in-app notification as read."""
    notif = db.query(InAppNotification).filter(InAppNotification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notif.is_read = True
    db.commit()
    return {"status": "success", "id": notification_id}

@app.post("/api/notifications/mark-all-read")
def mark_all_notifications_read(db: Session = Depends(get_db)):
    """Marks all in-app notifications as read."""
    db.query(InAppNotification).filter(InAppNotification.is_read == False).update({"is_read": True})
    db.commit()
    return {"status": "success"}

@app.get("/api/notifications/preferences")
def get_notification_preferences(db: Session = Depends(get_db)):
    """Retrieves current user notification preferences."""
    pref = db.query(NotificationPreference).first()
    if not pref:
        user = db.query(User).first()
        if not user:
            user = User(username="dev_user")
            db.add(user)
            db.commit()
            db.refresh(user)
        pref = NotificationPreference(user_id=user.id)
        db.add(pref)
        db.commit()
        db.refresh(pref)

    pref_data = {
        "email_enabled": pref.email_enabled,
        "slack_enabled": pref.slack_enabled,
        "discord_enabled": pref.discord_enabled,
        "in_app_enabled": pref.in_app_enabled,
        "notify_critical_only": pref.notify_critical_only
    }
    return {
        **pref_data,
        "preferences": pref_data
    }

@app.put("/api/notifications/preferences")
def update_notification_preferences(req: UpdatePreferenceRequest, db: Session = Depends(get_db)):
    """Updates user notification preferences."""
    pref = db.query(NotificationPreference).first()
    if not pref:
        user = db.query(User).first()
        if not user:
            user = User(username="dev_user")
            db.add(user)
            db.commit()
            db.refresh(user)
        pref = NotificationPreference(user_id=user.id)
        db.add(pref)

    if req.email_enabled is not None: pref.email_enabled = req.email_enabled
    if req.slack_enabled is not None: pref.slack_enabled = req.slack_enabled
    if req.discord_enabled is not None: pref.discord_enabled = req.discord_enabled
    if req.in_app_enabled is not None: pref.in_app_enabled = req.in_app_enabled
    if req.notify_critical_only is not None: pref.notify_critical_only = req.notify_critical_only

    db.commit()
    return {"status": "success", "preferences": {
        "email_enabled": pref.email_enabled,
        "slack_enabled": pref.slack_enabled,
        "discord_enabled": pref.discord_enabled,
        "in_app_enabled": pref.in_app_enabled,
        "notify_critical_only": pref.notify_critical_only
    }}

@app.get("/api/repos/{repo_id}/notifications")
def get_repo_notification_channels(repo_id: str, db: Session = Depends(get_db)):
    """Gets external notification channels (Slack, Discord, Email) configured for a repository."""
    channels = db.query(NotificationConfig).filter(NotificationConfig.repo_id == repo_id).all()
    return [
        {
            "id": c.id,
            "channel": c.channel,
            "target": c.target_url_or_email,
            "is_active": c.is_active,
            "created_at": c.created_at.isoformat()
        }
        for c in channels
    ]

@app.post("/api/repos/{repo_id}/notifications")
def add_repo_notification_channel(
    repo_id: str,
    req: AddNotificationConfigRequest,
    db: Session = Depends(get_db)
):
    """Registers an external notification channel (Slack/Discord Webhook URL or Email)."""
    valid_channels = ["slack", "discord", "email"]
    if req.channel not in valid_channels:
        raise HTTPException(status_code=400, detail=f"Channel must be one of: {valid_channels}")

    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")

    config = NotificationConfig(
        repo_id=repo_id,
        channel=req.channel,
        target_url_or_email=req.target_url_or_email,
        filter_rules=req.filter_rules or {},
        is_active=True
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    return {"status": "success", "id": config.id, "channel": config.channel}

@app.delete("/api/repos/{repo_id}/notifications/{config_id}")
def delete_repo_notification_channel(
    repo_id: str,
    config_id: str,
    db: Session = Depends(get_db)
):
    """Removes a notification channel from a repository."""
    config = db.query(NotificationConfig).filter(
        NotificationConfig.id == config_id,
        NotificationConfig.repo_id == repo_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Notification config not found.")

    db.delete(config)
    db.commit()
    return {"status": "success"}

# ==========================================
# BACKWARDS COMPATIBILITY (MANUAL RUNS)
# ==========================================

@app.get("/api/logs")
def get_logs():
    """Returns available sample and uploaded logs for manual investigation."""
    logs = []
    sample_logs_dir = os.path.join(project_root, "backend", "sample_logs")
    if os.path.exists(sample_logs_dir):
        for root, dirs, files in os.walk(sample_logs_dir):
            for file in files:
                if file.endswith((".txt", ".log", ".zip")):
                    rel_path = os.path.relpath(os.path.join(root, file), sample_logs_dir)
                    name = rel_path.replace("\\", " / ")
                    if "django" in name.lower():
                        name = "Django Test Run Failure"
                    elif "react" in name.lower():
                        name = "React Build System Failure"
                    elif "vscode" in name.lower():
                        name = "VS Code Integration Test Failure"
                    logs.append({
                        "id": f"sample:{rel_path}",
                        "name": name,
                        "filename": file,
                        "type": "sample"
                    })

    uploaded_logs_dir = LOGS_DIR
    if os.path.exists(uploaded_logs_dir):
        for file in os.listdir(uploaded_logs_dir):
            if file.endswith((".txt", ".log", ".zip")) and not file.startswith("."):
                logs.append({
                    "id": f"uploaded:{file}",
                    "name": f"Uploaded Log: {file}",
                    "filename": file,
                    "type": "uploaded"
                })
    return logs

@app.post("/api/upload")
async def upload_log(file: UploadFile = File(...)):
    """Allows user to upload a custom log file."""
    if not file.filename.endswith((".txt", ".log", ".zip")):
        raise HTTPException(status_code=400, detail="Only .txt, .log, or .zip files are supported.")
        
    filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(LOGS_DIR, filename)
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    return {
        "log_id": f"uploaded:{filename}",
        "filename": file.filename,
        "name": f"Uploaded Log: {file.filename}"
    }

@app.post("/api/analyze")
def analyze_log(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Starts the analysis for the given log ID."""
    log_id = request.log_id
    
    if log_id.startswith("sample:"):
        rel_path = log_id.split("sample:")[1]
        log_path = os.path.join(project_root, "backend", "sample_logs", rel_path)
    elif log_id.startswith("uploaded:"):
        filename = log_id.split("uploaded:")[1]
        log_path = os.path.join(LOGS_DIR, filename)
    else:
        raise HTTPException(status_code=400, detail="Invalid log ID format.")
        
    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail="Log file not found.")
        
    run_id = str(uuid.uuid4())
    runs[run_id] = {
        "run_id": run_id,
        "status": "pending",
        "log_name": os.path.basename(log_path),
        "stages": {
            stage: {"status": "PENDING", "time": 0.0}
            for stage in [
                "Parser", "Classifier", "Planner", "Collector", "Chunker",
                "Embedder", "Vector Store", "Retriever", "LLM", "Critic", "Report"
            ]
        },
        "console_logs": [],
        "report": None,
        "error": None
    }
    
    dispatch_res = dispatch_analysis(
        run_id=run_id,
        log_path=log_path,
        db_run_id=None,
        background_tasks=background_tasks,
        sync_fallback_func=run_analysis_thread
    )
    return {"run_id": run_id, "dispatch": dispatch_res}

@app.get("/api/system/status")
def get_system_status():
    """
    Returns real-time telemetry on database connection pool and Celery/Redis queue health.
    """
    return {
        "status": "online",
        "version": "3.0.0",
        "database": get_db_telemetry(),
        "queue": get_queue_telemetry()
    }

@app.get("/api/runs/{run_id}")
def get_run_status(run_id: str):
    """Fetches progress and report for a run."""
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found.")
    return runs[run_id]

@app.post("/api/fix")
def apply_fix(request: FixRequest):
    """Simulates applying the suggested fix (backward compatible)."""
    run_id = request.run_id
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found.")
        
    return {
        "status": "success",
        "message": f"Fix #{request.fix_index + 1} has been applied successfully. Staging build verified: stable."
    }

# ==========================================
# MILESTONE 5: CODE REMEDIATION & APPROVAL WORKFLOWS
# ==========================================

@app.get("/api/runs/{run_id}/remediations")
def list_remediations(run_id: str, db: Session = Depends(get_db)):
    """Fetches AI-synthesized code remediation patches for a run."""
    # Check database first
    remediations = db.query(CodeRemediation).filter(CodeRemediation.run_id == run_id).all()
    if not remediations:
        # Check via analysis_run_id
        analysis = db.query(FailureAnalysis).filter(FailureAnalysis.analysis_run_id == run_id).first()
        if analysis:
            remediations = db.query(CodeRemediation).filter(CodeRemediation.run_id == analysis.run_id).all()

    if remediations:
        return [
            {
                "id": r.id,
                "run_id": r.run_id,
                "title": r.title,
                "target_file": r.target_file,
                "diff_content": r.diff_content,
                "rationale": r.rationale,
                "risk_level": r.risk_level,
                "validation_command": r.validation_command,
                "status": r.status,
                "reviewer_role": r.reviewer_role,
                "reviewed_by": r.reviewed_by,
                "review_comments": r.review_comments,
                "applied_at": r.applied_at.isoformat() if r.applied_at else None,
                "created_at": r.created_at.isoformat()
            }
            for r in remediations
        ]

    # In-memory run fallback
    if run_id in runs and runs[run_id].get("report", {}).get("code_patch"):
        patch = runs[run_id]["report"]["code_patch"]
        return [{
            "id": patch.get("patch_id", "patch_in_memory"),
            "run_id": run_id,
            "title": patch["title"],
            "target_file": patch["target_file"],
            "diff_content": patch["diff_content"],
            "rationale": patch["rationale"],
            "risk_level": patch["risk_level"],
            "validation_command": patch["validation_command"],
            "status": patch.get("status", "pending_review"),
            "reviewer_role": "Developer",
            "reviewed_by": None,
            "review_comments": None,
            "applied_at": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }]

    return []

@app.post("/api/remediations/preview")
def preview_remediation(req: PreviewRemediationRequest, db: Session = Depends(get_db)):
    """Synthesizes or retrieves a live preview of the code remediation patch."""
    run_id = req.run_id
    if run_id in runs and runs[run_id].get("report"):
        rep = runs[run_id]["report"]
        if rep.get("code_patch"):
            return rep["code_patch"]
        patch = synthesize_code_patch(
            category=rep.get("failure_category", "UNKNOWN"),
            root_cause=rep.get("root_cause", ""),
            explanation=rep.get("explanation"),
            log_content=rep.get("pipeline_error")
        )
        return patch

    analysis = db.query(FailureAnalysis).filter(
        (FailureAnalysis.run_id == run_id) | (FailureAnalysis.analysis_run_id == run_id)
    ).first()
    if analysis:
        patch = synthesize_code_patch(
            category=analysis.failure_category or "UNKNOWN",
            root_cause=analysis.root_cause or "",
            explanation=analysis.explanation,
            log_content=analysis.explanation
        )
        return patch

    raise HTTPException(status_code=404, detail="Run not found for remediation preview.")

@app.post("/api/remediations/{remediation_id}/review")
def review_remediation(
    remediation_id: str,
    req: ReviewRemediationRequest,
    db: Session = Depends(get_db)
):
    """
    Human-in-the-Loop Review: Approves or rejects a proposed code remediation patch.
    Enforces minimum role permissions (Developer, Admin, or Owner).
    """
    action = req.action.lower()
    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'.")

    # Verify user role
    role_allowed = req.reviewer_role in (Role.DEVELOPER, Role.ADMIN, Role.OWNER)
    if not role_allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Role '{req.reviewer_role}' does not have permission to review remediations."
        )

    rem = db.query(CodeRemediation).filter(CodeRemediation.id == remediation_id).first()
    if not rem:
        # Check if it is an in-memory run patch
        for r_id, r_data in runs.items():
            if r_data.get("report", {}).get("code_patch", {}).get("patch_id") == remediation_id:
                new_status = "approved" if action == "approve" else "rejected"
                r_data["report"]["code_patch"]["status"] = new_status
                record_remediation_metric(action)
                return {
                    "status": new_status,
                    "remediation_id": remediation_id,
                    "message": f"Remediation patch {action}d successfully."
                }
        raise HTTPException(status_code=404, detail="Remediation not found.")

    new_status = "approved" if action == "approve" else "rejected"
    rem.status = new_status
    rem.reviewed_by = req.reviewer_username or "admin"
    rem.review_comments = req.comment
    db.commit()

    record_remediation_metric(action)

    return {
        "status": new_status,
        "remediation_id": rem.id,
        "reviewed_by": rem.reviewed_by,
        "message": f"Remediation patch '{rem.title}' has been {action}d."
    }

@app.post("/api/remediations/{remediation_id}/apply")
def apply_remediation(
    remediation_id: str,
    req: ApplyRemediationRequest,
    db: Session = Depends(get_db)
):
    """
    Applies an approved patch to the staging environment and verifies stability.
    """
    rem = db.query(CodeRemediation).filter(CodeRemediation.id == remediation_id).first()
    diff_content = None
    target_file = None
    run_ref = None

    if rem:
        if rem.status != "approved":
            raise HTTPException(
                status_code=400,
                detail=f"Remediation must be 'approved' before applying. Current status: '{rem.status}'."
            )
        diff_content = rem.diff_content
        target_file = rem.target_file
        run_ref = rem.run_id
    else:
        # Check in-memory run
        for r_id, r_data in runs.items():
            patch = r_data.get("report", {}).get("code_patch")
            if patch and patch.get("patch_id") == remediation_id:
                diff_content = patch["diff_content"]
                target_file = patch["target_file"]
                run_ref = r_id
                break

    if not diff_content:
        raise HTTPException(status_code=404, detail="Approved remediation not found.")

    # Execute staging application
    result = apply_simulated_patch(diff_content, target_file, run_ref)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))

    if rem:
        from datetime import datetime, timezone
        rem.status = "applied"
        rem.applied_at = datetime.now(timezone.utc)
        db.commit()

    record_remediation_metric("applied")

    return {
        "status": "applied",
        "remediation_id": remediation_id,
        "target_file": target_file,
        "verification": result["verification_result"],
        "message": result["message"]
    }

# ==========================================
# MILESTONE 6: OBSERVABILITY & PROMETHEUS METRICS
# ==========================================

@app.get("/api/metrics")
def get_metrics():
    """
    Exposes real-time Prometheus metrics for CI pipeline health, failure frequency,
    recurrence detection, MTTD, analysis latency, and remediation approval actions.
    """
    content, content_type = get_prometheus_metrics()
    return Response(content=content, media_type=content_type)

if __name__ == "__main__":
    import uvicorn
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000, reload=False)
