"""
Prometheus Metrics & Observability Telemetry Service (Milestone 6)

Exposes real-time Prometheus metrics for CI pipeline failure frequency, MTTD,
analysis duration, recurrence amplification, remediation approvals, and alert routing.
"""

import time
from typing import Dict, Any, Optional

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if PROMETHEUS_AVAILABLE:
    # Dedicated registry to prevent global namespace pollution
    registry = CollectorRegistry(auto_describe=True)

    # 1. Pipeline Failure Counters
    FAILURES_TOTAL = Counter(
        "pipeline_failures_total",
        "Total count of pipeline build failures ingested via webhooks or uploads",
        ["repo", "failure_type", "severity_tier"],
        registry=registry
    )

    # 2. Historical Recurrence Counter
    RECURRENCE_TOTAL = Counter(
        "pipeline_recurrence_total",
        "Total count of recurrent failure events detected via error signatures",
        ["repo", "severity_tier"],
        registry=registry
    )

    # 3. Notification Dispatch Counter
    NOTIFICATIONS_TOTAL = Counter(
        "pipeline_notifications_sent_total",
        "Total notifications dispatched across routing channels",
        ["channel", "severity"],
        registry=registry
    )

    # 4. Remediation Workflow Counter
    REMEDIATIONS_TOTAL = Counter(
        "pipeline_remediations_total",
        "Total count of AI code remediation proposals and approval actions",
        ["status"],
        registry=registry
    )

    # 5. Analysis Duration Histogram
    ANALYSIS_DURATION = Histogram(
        "pipeline_analysis_duration_seconds",
        "Duration of the 11-stage AI diagnostic pipeline",
        ["status"],
        buckets=(1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0),
        registry=registry
    )

    # 6. Mean Time To Detect (MTTD) Gauge
    MTTD_GAUGE = Gauge(
        "pipeline_mttd_seconds",
        "Estimated Mean Time To Detect failures in seconds",
        ["repo"],
        registry=registry
    )

    # 7. Queue Depth Gauge
    QUEUE_DEPTH = Gauge(
        "pipeline_queue_depth",
        "Current number of pending or queued tasks in the execution engine",
        ["queue_mode"],
        registry=registry
    )

    # Initial baseline seeds
    QUEUE_DEPTH.labels(queue_mode="celery").set(0)
    QUEUE_DEPTH.labels(queue_mode="local_async").set(0)

def record_failure_metric(repo: str, failure_type: str, severity_tier: str = "HIGH"):
    """Increments the pipeline failure counter."""
    if PROMETHEUS_AVAILABLE:
        FAILURES_TOTAL.labels(
            repo=repo or "default",
            failure_type=failure_type or "UnknownError",
            severity_tier=severity_tier or "MEDIUM"
        ).inc()

def record_recurrence_metric(repo: str, severity_tier: str = "CRITICAL"):
    """Increments recurrent failure counter."""
    if PROMETHEUS_AVAILABLE:
        RECURRENCE_TOTAL.labels(
            repo=repo or "default",
            severity_tier=severity_tier or "CRITICAL"
        ).inc()

def record_notification_metric(channel: str, severity: str = "critical"):
    """Increments notification dispatch counter."""
    if PROMETHEUS_AVAILABLE:
        NOTIFICATIONS_TOTAL.labels(
            channel=channel or "in_app",
            severity=severity or "critical"
        ).inc()

def record_remediation_metric(status: str):
    """Increments remediation approval action (proposed, approved, rejected, applied)."""
    if PROMETHEUS_AVAILABLE:
        REMEDIATIONS_TOTAL.labels(status=status).inc()

def record_analysis_duration(duration_seconds: float, status: str = "completed"):
    """Records the duration of pipeline analysis."""
    if PROMETHEUS_AVAILABLE:
        ANALYSIS_DURATION.labels(status=status).observe(duration_seconds)

def set_mttd_metric(repo: str, mttd_seconds: float):
    """Sets current MTTD for a repository."""
    if PROMETHEUS_AVAILABLE:
        MTTD_GAUGE.labels(repo=repo or "default").set(mttd_seconds)

def get_prometheus_metrics() -> tuple[bytes, str]:
    """
    Renders Prometheus metrics exposition.
    Returns: (content_bytes, content_type_header)
    """
    if PROMETHEUS_AVAILABLE:
        return generate_latest(registry), CONTENT_TYPE_LATEST
    
    # Minimal fallback text format
    fallback_text = (
        "# HELP pipeline_failures_total Total count of pipeline build failures\n"
        "# TYPE pipeline_failures_total counter\n"
        "pipeline_failures_total{repo=\"default\",failure_type=\"Generic\"} 0\n"
    )
    return fallback_text.encode("utf-8"), "text/plain; version=0.0.4; charset=utf-8"
