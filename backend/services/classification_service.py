"""
Advanced Failure Classification & Composite Severity Scoring Engine (Milestone 5)

Performs deep taxonomy classification across 8 granular failure archetypes and computes
a multi-factor composite severity score (0.0 - 1.0) based on blast radius, branch criticality,
and recurrence amplification.
"""

import re
from enum import Enum
from typing import Dict, Any, List, Optional

class FailureCategory(str, Enum):
    DEPENDENCY_INCOMPATIBILITY = "DEPENDENCY_INCOMPATIBILITY"
    FLAKY_TEST = "FLAKY_TEST"
    ASSERTION_FAILURE = "ASSERTION_FAILURE"
    INFRASTRUCTURE_TIMEOUT = "INFRASTRUCTURE_TIMEOUT"
    SECRETS_CREDENTIALS_EXPIRATION = "SECRETS_CREDENTIALS_EXPIRATION"
    BUILD_SYNTAX_ERROR = "BUILD_SYNTAX_ERROR"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    WORKFLOW_CONFIG_ERROR = "WORKFLOW_CONFIG_ERROR"
    UNKNOWN = "UNKNOWN"

# Base intrinsic risk by failure archetype (0.0 to 1.0)
CATEGORY_BASE_RISK = {
    FailureCategory.SECRETS_CREDENTIALS_EXPIRATION: 0.85,
    FailureCategory.RESOURCE_EXHAUSTION: 0.80,
    FailureCategory.DEPENDENCY_INCOMPATIBILITY: 0.70,
    FailureCategory.BUILD_SYNTAX_ERROR: 0.65,
    FailureCategory.ASSERTION_FAILURE: 0.60,
    FailureCategory.WORKFLOW_CONFIG_ERROR: 0.55,
    FailureCategory.INFRASTRUCTURE_TIMEOUT: 0.50,
    FailureCategory.FLAKY_TEST: 0.30,
    FailureCategory.UNKNOWN: 0.40,
}

# Regex classifiers ordered by specificity
CLASSIFICATION_RULES = [
    (
        FailureCategory.SECRETS_CREDENTIALS_EXPIRATION,
        re.compile(r"(bad credentials|unauthorized|401 unauthorized|403 forbidden|secret.*not found|expired token|invalid api key|permission denied.*token)", re.I)
    ),
    (
        FailureCategory.RESOURCE_EXHAUSTION,
        re.compile(r"(out of memory|oom|exit code 137|memoryerror|heap out of memory|fatal error: call_and_retry_last|no space left on device)", re.I)
    ),
    (
        FailureCategory.DEPENDENCY_INCOMPATIBILITY,
        re.compile(r"(modulenotfounderror|no module named|importerror|package.*not found|could not find a version that satisfies|npm err! code e404|dependency.*conflict|incompatible architecture|cannot resolve dependency)", re.I)
    ),
    (
        FailureCategory.BUILD_SYNTAX_ERROR,
        re.compile(r"(syntaxerror|indentationerror|unexpected token|compilation error|typescript error|ts\d{4}:|cannot parse|syntax error)", re.I)
    ),
    (
        FailureCategory.FLAKY_TEST,
        re.compile(r"(flaky|intermittent|retry \d of \d|test timed out after.*ms|race condition|socket hang up)", re.I)
    ),
    (
        FailureCategory.ASSERTION_FAILURE,
        re.compile(r"(assertionerror|assert .* ==|expected:? .* but got|failed:? \d+ failed|fail: test_|failed test:)", re.I)
    ),
    (
        FailureCategory.INFRASTRUCTURE_TIMEOUT,
        re.compile(r"(job has exceeded the maximum execution time|context deadline exceeded|operation timed out|connection reset by peer|runner lost communication)", re.I)
    ),
    (
        FailureCategory.WORKFLOW_CONFIG_ERROR,
        re.compile(r"(invalid workflow file|you may need an action|unrecognized named-value|the template is not valid|error: action.*could not be found)", re.I)
    )
]

def classify_granular_failure(
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    log_snippet: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classifies a pipeline failure into a granular category with rationale and detection confidence.
    """
    corpus = f"{error_type or ''} {error_message or ''} {log_snippet or ''}".strip()
    
    for category, pattern in CLASSIFICATION_RULES:
        match = pattern.search(corpus)
        if match:
            matched_phrase = match.group(0)
            return {
                "category": category.value,
                "confidence": 0.95 if error_type and pattern.search(error_type) else 0.85,
                "matched_pattern": matched_phrase,
                "rationale": f"Identified {category.value} via trace signature: '{matched_phrase}'"
            }
            
    return {
        "category": FailureCategory.UNKNOWN.value,
        "confidence": 0.40,
        "matched_pattern": None,
        "rationale": "Pattern not matched against predefined archetypes; labeled generic failure."
    }

def compute_composite_severity(
    category: str,
    branch: str = "main",
    is_recurring: bool = False,
    recurrence_count: int = 1
) -> Dict[str, Any]:
    """
    Calculates a composite severity score (0.0 to 1.0) and blast radius tier:
    - Base risk from failure category
    - Branch amplification: +0.20 for main/prod/master branches
    - Recurrence escalation: +0.05 per recurrence (capped at +0.20)
    """
    try:
        cat_enum = FailureCategory(category)
    except Exception:
        cat_enum = FailureCategory.UNKNOWN

    base_score = CATEGORY_BASE_RISK.get(cat_enum, 0.40)
    factors = [f"Base risk for {cat_enum.value}: {base_score:.2f}"]

    # Branch amplification
    is_production_branch = branch.lower() in ("main", "master", "prod", "production", "release")
    branch_factor = 0.20 if is_production_branch else 0.05
    factors.append(f"Branch '{branch}' impact factor: +{branch_factor:.2f}")

    # Recurrence escalation
    recurrence_factor = 0.0
    if is_recurring or recurrence_count > 1:
        recurrence_factor = min(0.20, max(0.05, (recurrence_count - 1) * 0.05))
        factors.append(f"Recurrence escalation (count={recurrence_count}): +{recurrence_factor:.2f}")

    raw_score = base_score + branch_factor + recurrence_factor
    score = min(1.0, max(0.1, round(raw_score, 2)))

    # Determine Severity Tier
    if score >= 0.85:
        tier = "CRITICAL"
        blast_radius = "Production Blocking - Requires Immediate On-Call Escalation"
    elif score >= 0.65:
        tier = "HIGH"
        blast_radius = "Core CI Disruption - Impedes Deployment Staging"
    elif score >= 0.40:
        tier = "MEDIUM"
        blast_radius = "Component Test or Non-Blocking Branch Failure"
    else:
        tier = "LOW"
        blast_radius = "Flaky or Minor Quality Check"

    return {
        "severity_score": score,
        "severity_tier": tier,
        "blast_radius": blast_radius,
        "is_production_branch": is_production_branch,
        "evaluation_factors": factors
    }
