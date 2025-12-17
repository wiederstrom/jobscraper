"""
FastAPI dependencies for dependency injection
"""

from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session for FastAPI endpoints.

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
