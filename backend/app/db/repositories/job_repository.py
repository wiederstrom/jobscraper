"""
Job repository for job-specific database operations
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc

from app.db.models import Job
from app.db.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Repository for Job model with specialized queries"""

    def __init__(self, db: Session):
        super().__init__(Job, db)

    def get_by_url(self, url: str) -> Optional[Job]:
        """Get job by URL (used for deduplication)"""
        return self.get_by_field("url", url)

    def exists_by_url(self, url: str) -> bool:
        """Check if job exists by URL"""
        return self.exists(url=url)

    def get_all_with_filters(
        self,
        source: Optional[str] = None,
        keyword: Optional[str] = None,
        search: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        is_hidden: Optional[bool] = False,
        applied: Optional[bool] = None,
        status: Optional[str] = None,
        date_range: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Job]:
        """
        Get jobs with multiple filters.

        Args:
            source: Filter by source (FINN or NAV)
            keyword: Filter by keyword (substring match)
            search: Search in title, company, description (substring match)
            is_favorite: Filter by favorite status
            is_hidden: Filter by hidden status (default: False to exclude hidden)
            applied: Filter by applied status
            status: Filter by job status (ACTIVE, INACTIVE, EXPIRED)
            date_range: Filter by date range (7days, 30days, 3months, all)
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of jobs matching filters
        """
        query = self.db.query(Job)

        # Apply filters
        if source:
            query = query.filter(Job.source == source)

        if keyword:
            query = query.filter(Job.keywords.ilike(f"%{keyword}%"))

        if search:
            search_filter = or_(
                Job.title.ilike(f"%{search}%"),
                Job.company.ilike(f"%{search}%"),
                Job.description.ilike(f"%{search}%"),
                Job.summary.ilike(f"%{search}%"),
            )
            query = query.filter(search_filter)

        if is_favorite is not None:
            query = query.filter(Job.is_favorite == is_favorite)

        if is_hidden is not None:
            query = query.filter(Job.is_hidden == is_hidden)

        if applied is not None:
            query = query.filter(Job.applied == applied)

        if status:
            query = query.filter(Job.status == status)

        # Date range filter
        if date_range and date_range != 'all':
            if date_range == '7days':
                cutoff = datetime.now() - timedelta(days=7)
            elif date_range == '30days':
                cutoff = datetime.now() - timedelta(days=30)
            elif date_range == '3months':
                cutoff = datetime.now() - timedelta(days=90)
            else:
                cutoff = None

            if cutoff:
                query = query.filter(Job.scraped_date >= cutoff)

        # Order by scraped_date descending (newest first)
        query = query.order_by(desc(Job.scraped_date))

        # Pagination
        return query.offset(skip).limit(limit).all()

    def update_job_metadata(
        self,
        job_id: int,
        is_favorite: Optional[bool] = None,
        is_hidden: Optional[bool] = None,
        applied: Optional[bool] = None,
        notes: Optional[str] = None,
    ) -> Optional[Job]:
        """
        Update job metadata (user interaction fields).

        Args:
            job_id: Job ID
            is_favorite: Mark as favorite
            is_hidden: Hide job
            applied: Mark as applied
            notes: User notes

        Returns:
            Updated job or None if not found
        """
        job = self.get_by_id(job_id)
        if not job:
            return None

        updates = {}
        if is_favorite is not None:
            updates["is_favorite"] = is_favorite

        if is_hidden is not None:
            updates["is_hidden"] = is_hidden

        if applied is not None:
            updates["applied"] = applied
            if applied:
                updates["applied_date"] = datetime.now()
            else:
                updates["applied_date"] = None

        if notes is not None:
            updates["notes"] = notes

        return self.update(job, updates)

    def mark_as_inactive(self, job_ids: List[int]) -> int:
        """
        Mark multiple jobs as inactive.

        Args:
            job_ids: List of job IDs to mark inactive

        Returns:
            Number of jobs updated
        """
        count = (
            self.db.query(Job)
            .filter(Job.id.in_(job_ids))
            .update({"status": "INACTIVE"}, synchronize_session=False)
        )
        self.db.commit()
        return count

    def get_statistics(
        self,
        source: Optional[str] = None,
        is_hidden: bool = False,
    ) -> Dict[str, Any]:
        """
        Get job statistics.

        Args:
            source: Filter by source
            is_hidden: Include hidden jobs

        Returns:
            Dictionary with statistics
        """
        query = self.db.query(Job)

        if source:
            query = query.filter(Job.source == source)

        if not is_hidden:
            query = query.filter(Job.is_hidden == False)

        total = query.count()
        favorites = query.filter(Job.is_favorite == True).count()
        applied = query.filter(Job.applied == True).count()

        # Jobs by source
        finn_count = query.filter(Job.source == "FINN").count()
        nav_count = query.filter(Job.source == "NAV").count()

        # Jobs by status
        active_count = query.filter(Job.status == "ACTIVE").count()
        inactive_count = query.filter(Job.status == "INACTIVE").count()
        expired_count = query.filter(Job.status == "EXPIRED").count()

        # New jobs last 7 days
        seven_days_ago = datetime.now() - timedelta(days=7)
        new_jobs = query.filter(Job.scraped_date >= seven_days_ago).count()

        return {
            "total_jobs": total,
            "favorites": favorites,
            "applied": applied,
            "sources": {
                "FINN": finn_count,
                "NAV": nav_count,
            },
            "status": {
                "ACTIVE": active_count,
                "INACTIVE": inactive_count,
                "EXPIRED": expired_count,
            },
            "new_last_7_days": new_jobs,
        }

    def get_recent_jobs(self, limit: int = 10) -> List[Job]:
        """Get most recently scraped jobs"""
        return (
            self.db.query(Job)
            .filter(Job.is_hidden == False)
            .order_by(desc(Job.scraped_date))
            .limit(limit)
            .all()
        )

    def get_jobs_by_keyword(
        self, keyword: str, skip: int = 0, limit: int = 100
    ) -> List[Job]:
        """Get all jobs found by a specific keyword"""
        return self.get_multi_by_field("keywords", keyword, skip, limit)

    def get_expired_jobs(self) -> List[Job]:
        """
        Get jobs that should be marked as expired.
        Jobs are expired if:
        - expire_date has passed
        - scraped_date is older than 6 months
        """
        now = datetime.now()
        six_months_ago = now - timedelta(days=180)

        return (
            self.db.query(Job)
            .filter(
                or_(
                    Job.expire_date < now,
                    and_(
                        Job.scraped_date < six_months_ago,
                        Job.status == "ACTIVE"
                    )
                )
            )
            .all()
        )

    def bulk_create(self, jobs_data: List[Dict[str, Any]]) -> List[Job]:
        """
        Create multiple jobs in bulk.

        Args:
            jobs_data: List of job dictionaries

        Returns:
            List of created Job objects
        """
        jobs = [Job(**data) for data in jobs_data]
        self.db.bulk_save_objects(jobs, return_defaults=True)
        self.db.commit()
        return jobs
