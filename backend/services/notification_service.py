import os
import time
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.db.models import (
    User, Repository, RepositoryMember, WorkflowRun, 
    FailureAnalysis, InAppNotification, NotificationConfig, NotificationPreference
)
from backend.services.rbac_service import Role

logger = logging.getLogger("backend.notifications")

# In-memory throttle cache: maps (repo_id, error_signature, branch) -> last_dispatched_timestamp
_ALERT_THROTTLE_CACHE: Dict[str, float] = {}
THROTTLE_WINDOW_SECONDS = 600.0  # 10 minutes deduplication window

class EventType:
    MAIN_BRANCH_FAILURE = "main_branch_failure"
    REPEATED_FAILURE = "repeated_failure"
    BRANCH_FAILURE = "branch_failure"
    ACCESS_CHANGE = "access_change"

class Severity:
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

def get_routing_roles(event_type: str) -> List[str]:
    """
    Role-Based Routing Matrix:
    - Main branch failure -> Admin + Developers + Owner
    - Repeated failure -> Admin + Owner
    - Non-critical branch failure -> Developer
    - Repository access change -> Owner
    """
    if event_type == EventType.REPEATED_FAILURE:
        return [Role.OWNER, Role.ADMIN]
    elif event_type == EventType.MAIN_BRANCH_FAILURE:
        return [Role.OWNER, Role.ADMIN, Role.DEVELOPER]
    elif event_type == EventType.BRANCH_FAILURE:
        return [Role.DEVELOPER]
    elif event_type == EventType.ACCESS_CHANGE:
        return [Role.OWNER]
    return [Role.OWNER, Role.ADMIN]

def is_alert_throttled(repo_id: str, signature: str, branch: str) -> bool:
    """
    Returns True if an alert with identical signature has already been dispatched
    within the deduplication throttle window.
    """
    cache_key = f"{repo_id}:{signature}:{branch}"
    last_time = _ALERT_THROTTLE_CACHE.get(cache_key)
    if last_time and (time.time() - last_time) < THROTTLE_WINDOW_SECONDS:
        return True
    return False

def record_alert_dispatched(repo_id: str, signature: str, branch: str):
    """Updates the throttle cache timestamp for an alert."""
    cache_key = f"{repo_id}:{signature}:{branch}"
    _ALERT_THROTTLE_CACHE[cache_key] = time.time()

class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def determine_event_type(self, branch: str, is_recurring: bool) -> tuple[str, str]:
        """
        Determines the event type and severity based on branch and recurrence criteria.
        """
        critical_branches = {"main", "master", "prod", "production", "release"}
        is_main = branch.lower() in critical_branches

        if is_recurring:
            return EventType.REPEATED_FAILURE, Severity.CRITICAL
        elif is_main:
            return EventType.MAIN_BRANCH_FAILURE, Severity.CRITICAL
        else:
            return EventType.BRANCH_FAILURE, Severity.WARNING

    def dispatch_failure_notification(
        self,
        workflow_run: WorkflowRun,
        analysis: FailureAnalysis
    ) -> Dict[str, Any]:
        """
        Orchestrates intelligent role-aware notification routing with alert deduplication.
        """
        repo = workflow_run.repository
        if not repo:
            return {"status": "skipped", "reason": "Repository not found."}

        event_type, severity = self.determine_event_type(
            branch=workflow_run.head_branch,
            is_recurring=analysis.is_recurring
        )

        signature = analysis.error_signature or "default"

        # Check deduplication window
        if is_alert_throttled(repo.id, signature, workflow_run.head_branch):
            logger.info(f"Alert throttled for {repo.full_name} ({signature}) on branch {workflow_run.head_branch}")
            return {
                "status": "throttled",
                "reason": "Duplicate alert suppressed within throttle window."
            }

        # 1. Determine target application roles
        target_roles = get_routing_roles(event_type)

        # 2. Query repository members matching these target roles
        members = (
            self.db.query(RepositoryMember)
            .filter(
                RepositoryMember.repo_id == repo.id,
                RepositoryMember.app_role.in_(target_roles)
            )
            .all()
        )

        # Fallback: if repo has no explicit members yet, auto-enroll the primary user as Owner
        if not members:
            primary_user = self.db.query(User).first()
            if not primary_user:
                primary_user = User(username="dev_user", global_role="Admin")
                self.db.add(primary_user)
                self.db.commit()
                self.db.refresh(primary_user)
            
            member = RepositoryMember(
                user_id=primary_user.id,
                repo_id=repo.id,
                github_permission="admin",
                app_role=Role.OWNER
            )
            self.db.add(member)
            self.db.commit()
            if Role.OWNER in target_roles:
                members = [member]

        # 3. Format titles and messages
        title_prefix = "REPEATED FAILURE" if analysis.is_recurring else "BUILD FAILURE"
        title = f"[{title_prefix}] {repo.name} ({workflow_run.workflow_name})"

        message = (
            f"Build failure on branch '{workflow_run.head_branch}' (commit {workflow_run.head_sha}).\n"
            f"Root cause: {analysis.root_cause}\n"
        )
        if analysis.is_recurring:
            message += f"Identified as recurrent (occurred {analysis.recurrence_count} times).\n"

        if analysis.suggested_fixes and len(analysis.suggested_fixes) > 0:
            message += f"Suggested fix: {analysis.suggested_fixes[0]}"

        dispatched_recipients = []

        # 4. Dispatch In-App Notifications
        for member in members:
            # Check user preferences if present
            pref = member.user.preference
            if pref and not pref.in_app_enabled:
                continue
            if pref and pref.notify_critical_only and severity != Severity.CRITICAL:
                continue

            notif = InAppNotification(
                user_id=member.user_id,
                repo_id=repo.id,
                run_id=workflow_run.id,
                title=title,
                message=message,
                severity=severity,
                event_type=event_type,
                is_read=False
            )
            self.db.add(notif)
            dispatched_recipients.append({
                "username": member.user.username,
                "role": member.app_role,
                "channel": "in_app"
            })

        self.db.commit()

        # 5. Dispatch External Webhook Channels (Slack / Discord)
        external_channels = (
            self.db.query(NotificationConfig)
            .filter(
                NotificationConfig.repo_id == repo.id,
                NotificationConfig.is_active == True
            )
            .all()
        )

        for channel in external_channels:
            if channel.channel == "slack":
                self._send_slack_alert(channel.target_url_or_email, repo, workflow_run, analysis, severity)
                dispatched_recipients.append({"channel": "slack", "target": channel.target_url_or_email[:25] + "..."})
            elif channel.channel == "discord":
                self._send_discord_alert(channel.target_url_or_email, repo, workflow_run, analysis, severity)
                dispatched_recipients.append({"channel": "discord", "target": channel.target_url_or_email[:25] + "..."})

        # Record dispatch timestamp for deduplication
        record_alert_dispatched(repo.id, signature, workflow_run.head_branch)

        return {
            "status": "dispatched",
            "event_type": event_type,
            "severity": severity,
            "recipients_count": len(dispatched_recipients),
            "recipients": dispatched_recipients
        }

    def _send_slack_alert(
        self,
        webhook_url: str,
        repo: Repository,
        run: WorkflowRun,
        analysis: FailureAnalysis,
        severity: str
    ):
        """Dispatches formatted Slack Webhook using Block Kit."""
        color = "#e02424" if severity == Severity.CRITICAL else "#e3a008"
        first_fix = analysis.suggested_fixes[0] if analysis.suggested_fixes else "Review CI run logs."
        payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": f"🚨 Build Failure: {repo.full_name}"}
                        },
                        {
                            "type": "section",
                            "fields": [
                                {"type": "mrkdwn", "text": f"*Workflow:*\n{run.workflow_name}"},
                                {"type": "mrkdwn", "text": f"*Branch:*\n`{run.head_branch}`"},
                                {"type": "mrkdwn", "text": f"*Commit:*\n`{run.head_sha}` - {run.commit_message}"},
                                {"type": "mrkdwn", "text": f"*Recurrence:*\n{'Recurring (' + str(analysis.recurrence_count) + 'x)' if analysis.is_recurring else 'Novel'}"}
                            ]
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*AI Diagnosis:*\n{analysis.root_cause}\n\n*Actionable Fix:*\n```{first_fix}```"
                            }
                        }
                    ]
                }
            ]
        }
        try:
            requests.post(webhook_url, json=payload, timeout=5)
        except Exception as e:
            logger.warning(f"Failed to deliver Slack webhook: {e}")

    def _send_discord_alert(
        self,
        webhook_url: str,
        repo: Repository,
        run: WorkflowRun,
        analysis: FailureAnalysis,
        severity: str
    ):
        """Dispatches Discord Embed."""
        color = 15548997 if severity == Severity.CRITICAL else 16753920
        first_fix = analysis.suggested_fixes[0] if analysis.suggested_fixes else "Review CI run logs."
        payload = {
            "embeds": [
                {
                    "title": f"🚨 CI Failure: {repo.full_name}",
                    "description": f"**Root Cause:** {analysis.root_cause}",
                    "color": color,
                    "fields": [
                        {"name": "Branch", "value": f"`{run.head_branch}`", "inline": True},
                        {"name": "Commit", "value": f"`{run.head_sha}`", "inline": True},
                        {"name": "Suggested Fix", "value": f"```{first_fix}```"}
                    ]
                }
            ]
        }
        try:
            requests.post(webhook_url, json=payload, timeout=5)
        except Exception as e:
            logger.warning(f"Failed to deliver Discord webhook: {e}")
