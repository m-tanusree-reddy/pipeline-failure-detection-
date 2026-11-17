"""Database package for Pipeline Failure Detection 2.0 & 3.0."""
from backend.db.session import engine, SessionLocal, get_db, init_db
from backend.db.models import (
    Base, User, Repository, RepositoryMember, WorkflowRun, 
    FailureAnalysis, NotificationConfig, InAppNotification, NotificationPreference
)

__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "Base",
    "User",
    "Repository",
    "RepositoryMember",
    "WorkflowRun",
    "FailureAnalysis",
    "NotificationConfig",
    "InAppNotification",
    "NotificationPreference"
]
