import os
from typing import Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Default to SQLite local database file in project root if not configured for PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pipeline_failure_2.db")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

INSECURE_DEFAULT_PASSWORDS = {
    "pipeline_secure_pass",
    "password",
    "postgres",
    "admin",
    "root",
    "123456",
    "secret"
}

def validate_db_security(db_url: str, environment: str = "development") -> bool:
    """
    Enforces enterprise database security:
    - Forbids SQLite in production.
    - Forbids hardcoded, default, or trivial database passwords in production.
    """
    env = environment.lower()
    if env in ("production", "prod"):
        if not db_url or db_url.startswith("sqlite"):
            raise ValueError(
                "Production Error: SQLite is not permitted in production. "
                "A secure PostgreSQL DATABASE_URL must be configured."
            )
        for insecure_pw in INSECURE_DEFAULT_PASSWORDS:
            if f":{insecure_pw}@" in db_url:
                raise ValueError(
                    f"Production Security Violation: Insecure database password detected (':{insecure_pw}@'). "
                    "You must configure a strong, unique secret via POSTGRES_PASSWORD / DATABASE_URL."
                )
    return True

# Validate database configuration security against current environment
validate_db_security(DATABASE_URL, ENVIRONMENT)

is_sqlite = DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    # Production PostgreSQL Connection Pool Tuning
    engine = create_engine(
        DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_pre_ping=True,      # Tests connection liveness on checkout
        pool_recycle=3600,       # Recycles connections every hour
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI dependency to yield database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    from backend.db.models import Base
    Base.metadata.create_all(bind=engine)

def get_db_telemetry() -> Dict[str, Any]:
    """Returns database connection status and dialect metrics."""
    dialect = "sqlite" if is_sqlite else "postgresql"
    try:
        with engine.connect() as conn:
            return {
                "dialect": dialect,
                "status": "connected",
                "pool_size": 1 if is_sqlite else engine.pool.size(),
                "overflow": 0 if is_sqlite else engine.pool.overflow()
            }
    except Exception as e:
        return {
            "dialect": dialect,
            "status": "error",
            "error": str(e)
        }
