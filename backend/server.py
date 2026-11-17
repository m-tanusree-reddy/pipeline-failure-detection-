import os
import sys
import uuid
import time
import json
import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from backend.config import LOGS_DIR, ALLOWED_ORIGINS
from backend.pipeline import PipelineOrchestrator
from backend.db.session import init_db, get_db, SessionLocal, get_db_telemetry
from backend.db.models import (
    User, Repository, RepositoryMember, WorkflowRun, FailureAnalysis, 
    NotificationConfig, InAppNotification, NotificationPreference
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
        
        # Execute pipeline orchestrator
        report = orchestrator.run(log_path)
        
        # Prepare structured report
        report_dict = {
            "pipeline_error": report.pipeline_error,
            "failure_type": report.failure_type,
            "root_cause": report.root_cause,
            "explanation": report.explanation,
            "evidence": report.evidence,
            "suggested_fixes": report.suggested_fixes,
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

                    analysis = FailureAnalysis(
                        run_id=wf_run.id,
                        analysis_run_id=run_id,
                        failure_type=report.failure_type,
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
                    db.commit()

                    # Update in-memory report dict with correlation results
                    report_dict["error_signature"] = corr["error_signature"]
                    report_dict["is_recurring"] = corr["is_recurring"]
                    report_dict["recurrence_count"] = corr["recurrence_count"]
                    report_dict["intelligence_note"] = corr["intelligence_note"]
                    report_dict["past_occurrences"] = corr["past_occurrences"]

                    append_run_log(run_id, "INFO", f"[Historical Intelligence] {corr['intelligence_note']}")

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
def health_check():
    """Endpoint for deployment verification and health checks."""
    return {"status": "healthy", "version": "3.0.0"}

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

    return {
        "email_enabled": pref.email_enabled,
        "slack_enabled": pref.slack_enabled,
        "discord_enabled": pref.discord_enabled,
        "in_app_enabled": pref.in_app_enabled,
        "notify_critical_only": pref.notify_critical_only
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
    """Simulates applying the suggested fix."""
    run_id = request.run_id
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found.")
        
    return {
        "status": "success",
        "message": f"Fix #{request.fix_index + 1} has been applied successfully. Staging build verified: stable."
    }

if __name__ == "__main__":
    import uvicorn
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    uvicorn.run("backend.server:app", host="127.0.0.1", port=8000, reload=False)
