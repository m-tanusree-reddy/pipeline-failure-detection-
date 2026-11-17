import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Float, Text, JSON
from sqlalchemy.orm import relationship
from backend.db.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    github_id = Column(String(64), unique=True, index=True, nullable=True)
    username = Column(String(128), unique=True, index=True, nullable=False)
    email = Column(String(256), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    global_role = Column(String(32), default="User")  # Admin or User
    created_at = Column(DateTime, default=utc_now)

    memberships = relationship("RepositoryMember", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("InAppNotification", back_populates="user", cascade="all, delete-orphan")
    preference = relationship("NotificationPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner = Column(String(128), nullable=False, index=True)
    name = Column(String(128), nullable=False, index=True)
    full_name = Column(String(256), unique=True, nullable=False, index=True) # e.g. "octocat/Hello-World"
    is_private = Column(Boolean, default=False)
    default_branch = Column(String(64), default="main")
    webhook_secret = Column(String(128), nullable=True)
    github_app_installation_id = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    members = relationship("RepositoryMember", back_populates="repository", cascade="all, delete-orphan")
    workflow_runs = relationship("WorkflowRun", back_populates="repository", cascade="all, delete-orphan")
    notifications = relationship("NotificationConfig", back_populates="repository", cascade="all, delete-orphan")
    in_app_notifications = relationship("InAppNotification", back_populates="repository", cascade="all, delete-orphan")

class RepositoryMember(Base):
    __tablename__ = "repository_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    repo_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    # GitHub permission level: "admin", "maintain", "write" / "push", "read" / "pull"
    github_permission = Column(String(32), nullable=False)
    # Application role: "Owner", "Admin", "Developer", "Viewer"
    app_role = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="memberships")
    repository = relationship("Repository", back_populates="members")

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repo_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    github_run_id = Column(String(64), index=True, nullable=True)
    run_number = Column(Integer, default=1)
    workflow_name = Column(String(256), default="CI Pipeline")
    head_branch = Column(String(128), default="main")
    head_sha = Column(String(64), nullable=True)
    commit_message = Column(String(512), nullable=True)
    event = Column(String(64), default="workflow_run")
    status = Column(String(32), default="completed") # queued, in_progress, completed
    conclusion = Column(String(32), default="failure") # success, failure, cancelled, timed_out
    log_path = Column(String(512), nullable=True)
    completed_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    repository = relationship("Repository", back_populates="workflow_runs")
    analysis = relationship("FailureAnalysis", back_populates="workflow_run", uselist=False, cascade="all, delete-orphan")

class FailureAnalysis(Base):
    __tablename__ = "failure_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False, unique=True)
    analysis_run_id = Column(String(64), nullable=True) # links to in-memory run_id for real-time streaming
    failure_type = Column(String(128), nullable=True)
    root_cause = Column(String(256), nullable=True)
    explanation = Column(Text, nullable=True)
    suggested_fixes = Column(JSON, default=list)
    evidence = Column(JSON, default=list)
    original_confidence = Column(Float, default=0.0)
    final_confidence = Column(Float, default=0.0)
    critic_status = Column(String(32), default="PASSED")
    critic_comments = Column(Text, nullable=True)
    
    # Milestone 5 & Improvement C: Historical Intelligence
    error_signature = Column(String(128), index=True, nullable=True)
    is_recurring = Column(Boolean, default=False)
    recurrence_count = Column(Integer, default=1)
    previous_run_id = Column(String(36), nullable=True)

    status = Column(String(32), default="completed") # pending, running, completed, failed
    created_at = Column(DateTime, default=utc_now)

    workflow_run = relationship("WorkflowRun", back_populates="analysis")

class NotificationConfig(Base):
    __tablename__ = "notification_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    repo_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    channel = Column(String(32), nullable=False) # "slack", "discord", "email", "in_app"
    target_url_or_email = Column(String(512), nullable=False)
    # JSON filter rules e.g. {"branches": ["main", "master"], "notify_on": ["failure"]}
    filter_rules = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    repository = relationship("Repository", back_populates="notifications")

class InAppNotification(Base):
    __tablename__ = "in_app_notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    repo_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=True)
    title = Column(String(256), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(32), default="critical") # "critical", "warning", "info"
    event_type = Column(String(64), default="branch_failure") # "main_branch_failure", "repeated_failure", "branch_failure", "access_change"
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="notifications")
    repository = relationship("Repository", back_populates="in_app_notifications")
    workflow_run = relationship("WorkflowRun")

class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    email_enabled = Column(Boolean, default=True)
    slack_enabled = Column(Boolean, default=True)
    discord_enabled = Column(Boolean, default=True)
    in_app_enabled = Column(Boolean, default=True)
    notify_critical_only = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="preference")
