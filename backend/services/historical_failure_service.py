import re
import hashlib
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from backend.db.models import WorkflowRun, FailureAnalysis

def normalize_error_trace(text: str) -> str:
    """
    Normalizes error strings by stripping specific memory addresses, line numbers,
    and timestamps to allow robust recurrence grouping.
    """
    if not text:
        return ""
    # Strip hex addresses like 0x7fa28c0a
    s = re.sub(r"0x[0-9a-fA-F]+", "0x...", text)
    # Strip timestamps like 2026-11-17T08:57:53
    s = re.sub(r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}", "", s)
    # Strip line numbers like line 42 -> line N
    s = re.sub(r"line \d+", "line N", s)
    # Normalize whitespaces
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s[:300]

def generate_error_signature(failure_type: str, root_cause: str, raw_snippet: str = "") -> str:
    """
    Generates a deterministic 16-character SHA-256 signature from normalized failure attributes.
    """
    normalized = f"{normalize_error_trace(failure_type)}|{normalize_error_trace(root_cause)}|{normalize_error_trace(raw_snippet[:150])}"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest[:16]

class HistoricalFailureService:
    def __init__(self, db: Session):
        self.db = db

    def check_and_correlate_failure(
        self,
        repo_id: str,
        failure_type: str,
        root_cause: str,
        current_run_id: Optional[str] = None,
        error_snippet: str = ""
    ) -> Dict[str, Any]:
        """
        Analyzes an incoming failure against historical failures for this repository.
        Identifies recurrence, past commits where it failed, and prior root causes.
        """
        sig = generate_error_signature(failure_type, root_cause, error_snippet)

        # Query past analyses with same signature or failure type for this repo
        query = (
            self.db.query(FailureAnalysis, WorkflowRun)
            .join(WorkflowRun, FailureAnalysis.run_id == WorkflowRun.id)
            .filter(WorkflowRun.repo_id == repo_id)
        )
        if current_run_id:
            query = query.filter(WorkflowRun.id != current_run_id)

        all_matches = query.order_by(WorkflowRun.created_at.desc()).limit(10).all()

        # Find direct signature matches first, or failure_type matches
        signature_matches = [
            (fa, wf) for fa, wf in all_matches if fa.error_signature == sig
        ]

        if not signature_matches:
            # Check for close root-cause match
            norm_rc = normalize_error_trace(root_cause)
            signature_matches = [
                (fa, wf) for fa, wf in all_matches
                if fa.root_cause and norm_rc in normalize_error_trace(fa.root_cause)
            ]

        is_recurring = len(signature_matches) > 0
        recurrence_count = len(signature_matches) + 1

        past_occurrences = []
        previous_occurrence_id = None

        for idx, (fa, wf) in enumerate(signature_matches[:3]):
            if idx == 0:
                previous_occurrence_id = fa.id
            past_occurrences.append({
                "run_id": wf.id,
                "commit_sha": wf.head_sha,
                "branch": wf.head_branch,
                "timestamp": wf.created_at.isoformat() if wf.created_at else "",
                "workflow_name": wf.workflow_name,
                "root_cause": fa.root_cause,
                "suggested_fixes": fa.suggested_fixes[:2] if fa.suggested_fixes else []
            })

        # Generate contextual intelligence narrative
        if is_recurring:
            first_seen = past_occurrences[-1]
            intelligence_note = (
                f"RECURRING FAILURE DETECTED: This identical issue has been observed {recurrence_count} times in this repository. "
                f"It was previously encountered on branch '{past_occurrences[0]['branch']}' (commit {past_occurrences[0]['commit_sha']}). "
                f"Prior diagnosis: '{past_occurrences[0]['root_cause']}'."
            )
        else:
            intelligence_note = "NOVEL FAILURE: No matching failure signatures detected in historical repository records."

        return {
            "error_signature": sig,
            "is_recurring": is_recurring,
            "recurrence_count": recurrence_count,
            "previous_run_id": previous_occurrence_id,
            "past_occurrences": past_occurrences,
            "intelligence_note": intelligence_note
        }

