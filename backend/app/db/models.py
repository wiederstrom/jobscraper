"""
SQLAlchemy ORM models for job scraper database
Matches existing PostgreSQL schema
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, Column, Integer, String, Text, TIMESTAMP, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Job(Base):
    """Job posting model - matches existing 'jobs' table"""

    __tablename__ = "jobs"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Job details
    title = Column(Text, nullable=False)
    company = Column(Text, nullable=False)
    location = Column(Text, nullable=True)
    url = Column(Text, unique=True, nullable=False)  # Deduplication key
    source = Column(Text, nullable=False)  # 'FINN' or 'NAV'
    keywords = Column(Text, nullable=True)  # Search keyword that found this job

    # Job metadata
    deadline = Column(Text, nullable=True)
    job_type = Column(Text, nullable=True)
    published = Column(Text, nullable=True)
    scraped_date = Column(TIMESTAMP, nullable=False, default=func.now())

    # Content
    description = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)  # AI-generated summary

    # User interaction flags
    is_hidden = Column(Boolean, default=False, nullable=False)
    is_favorite = Column(Boolean, default=False, nullable=False)
    applied = Column(Boolean, default=False, nullable=False)
    applied_date = Column(TIMESTAMP, nullable=True)
    notes = Column(Text, nullable=True)

    # New fields for enhanced functionality
    last_checked = Column(TIMESTAMP, nullable=True)  # Last verification timestamp
    external_id = Column(Text, nullable=True)  # NAV API job ID
    status = Column(Text, default='ACTIVE', nullable=True)  # ACTIVE, INACTIVE, EXPIRED
    expire_date = Column(TIMESTAMP, nullable=True)  # Calculated expiry date

    # Indexes for performance
    __table_args__ = (
        Index('idx_jobs_url', 'url'),
        Index('idx_jobs_source', 'source'),
        Index('idx_jobs_status', 'status'),
        Index('idx_jobs_scraped_date', 'scraped_date'),
        Index('idx_jobs_external_id', 'external_id'),
    )

    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}', source='{self.source}')>"


class IrrelevantJob(Base):
    """Irrelevant jobs cache - prevents reprocessing filtered jobs"""

    __tablename__ = "irrelevant_jobs"

    url = Column(Text, primary_key=True)

    def __repr__(self):
        return f"<IrrelevantJob(url='{self.url}')>"


class SyncState(Base):
    """Sync state tracking for scrapers"""

    __tablename__ = "sync_state"

    source = Column(Text, primary_key=True)  # 'FINN' or 'NAV'
    last_sync = Column(TIMESTAMP, nullable=False)
    last_etag = Column(Text, nullable=True)  # For NAV API caching
    jobs_added_last_run = Column(Integer, default=0)
    jobs_removed_last_run = Column(Integer, default=0)

    def __repr__(self):
        return f"<SyncState(source='{self.source}', last_sync='{self.last_sync}')>"
