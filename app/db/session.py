"""
Database session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from contextlib import contextmanager
from typing import Generator

from app.config import settings
from app.db.models import Base


# Create database engine
engine = create_engine(
    settings.database_url,
    poolclass=NullPool,  # Disable connection pooling for serverless
    echo=False,  # Set to True for SQL logging during development
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints to get database session.

    Usage:
        @app.get("/jobs")
        def get_jobs(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database session (for use outside FastAPI).

    Usage:
        with get_db_context() as db:
            jobs = db.query(Job).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    This should be called on application startup.
    """
    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all tables - USE WITH CAUTION!
    Only for development/testing.
    """
    Base.metadata.drop_all(bind=engine)
