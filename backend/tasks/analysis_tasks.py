import os
import sys
import time
import logging
from typing import Optional, Dict, Any

from backend.celery_app import celery_app
from backend.db.session import SessionLocal
from backend.db.models import WorkflowRun, FailureAnalysis, CodeRemediation
from backend.pipeline import PipelineOrchestrator
from backend.services.historical_failure_service import HistoricalFailureService
from backend.services.notification_service import NotificationService
from backend.services.classification_service import classify_granular_failure, compute_composite_severity
from backend.services.remediation_service import synthesize_code_patch
from backend.services.metrics_service import (
    record_failure_metric, record_recurrence_metric, record_remediation_metric
)

logger = logging.getLogger("backend.tasks")

@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def analyze_failure_task(self, run_id: str, log_path: str, db_run_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Celery background worker task for asynchronous pipeline failure analysis.
    Features:
      - Idempotent execution
      - Exponential backoff retry on failure
      - Historical failure correlation
      - Automated role-based notifications
    """
    logger.info(f"[Celery Worker] Starting analysis for run_id={run_id}, attempt={self.request.retries + 1}")
    
    db = SessionLocal()
    try:
        # 1. Idempotency Check: if run is already analyzed and completed, skip reprocessing
        if db_run_id:
            wf_run = db.query(WorkflowRun).filter(WorkflowRun.id == db_run_id).first()
            if wf_run and wf_run.status == "completed" and wf_run.analysis:
                logger.info(f"[Celery Worker Idempotency] Run {db_run_id} is already completed. Skipping task.")
                return {
                    "status": "already_completed",
                    "run_id": run_id,
                    "db_run_id": db_run_id
                }
            if wf_run:
                wf_run.status = "running"
                db.commit()

        # 2. Run Pipeline Orchestrator
        orchestrator = PipelineOrchestrator()
        report = orchestrator.run(log_path)

        # 3. Correlation & Database Persistence
        if db_run_id:
            wf_run = db.query(WorkflowRun).filter(WorkflowRun.id == db_run_id).first()
            if wf_run:
                wf_run.status = "completed"

                # 1. Historical Failure Correlation
                hist_svc = HistoricalFailureService(db)
                corr = hist_svc.check_and_correlate_failure(
                    repo_id=wf_run.repo_id,
                    failure_type=report.failure_type,
                    root_cause=report.root_cause,
                    current_run_id=wf_run.id
                )

                # 2. Granular Failure Classification & Composite Severity Scoring (Milestone 5)
                gran_class = classify_granular_failure(
                    error_type=report.failure_type,
                    error_message=report.pipeline_error,
                    log_snippet=report.root_cause
                )
                sev_comp = compute_composite_severity(
                    category=gran_class["category"],
                    branch=wf_run.head_branch,
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

                # 3. AI Code-Level Patch Synthesis (Milestone 5)
                patch = synthesize_code_patch(
                    category=gran_class["category"],
                    root_cause=report.root_cause,
                    explanation=report.explanation,
                    evidence=report.evidence,
                    log_content=report.pipeline_error
                )
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

                # 4. Prometheus Metrics Recording (Milestone 6)
                repo_slug = wf_run.repository.full_name if wf_run.repository else "unknown"
                record_failure_metric(repo_slug, report.failure_type, sev_comp["severity_tier"])
                if corr["is_recurring"]:
                    record_recurrence_metric(repo_slug, sev_comp["severity_tier"])

                # 5. Dispatch notifications
                notif_svc = NotificationService(db)
                notif_svc.dispatch_failure_notification(wf_run, analysis)

        logger.info(f"[Celery Worker] Successfully analyzed run_id={run_id}")
        return {
            "status": "success",
            "run_id": run_id,
            "failure_type": report.failure_type,
            "root_cause": report.root_cause,
            "failure_category": gran_class["category"],
            "severity_score": sev_comp["severity_score"]
        }

    except Exception as exc:
        logger.error(f"[Celery Worker] Error analyzing run_id={run_id}: {exc}")
        
        # Exponential backoff retry: 10s, 20s, 40s
        retry_delay = 10 * (2 ** self.request.retries)
        if self.request.retries < self.max_retries:
            logger.info(f"[Celery Worker] Retrying task in {retry_delay}s (Attempt {self.request.retries + 1}/{self.max_retries})...")
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            # Mark workflow run as failed if final retry exhausted
            if db_run_id:
                try:
                    wf = db.query(WorkflowRun).filter(WorkflowRun.id == db_run_id).first()
                    if wf:
                        wf.status = "failed"
                        db.commit()
                except Exception:
                    pass
            raise exc
    finally:
        db.close()
