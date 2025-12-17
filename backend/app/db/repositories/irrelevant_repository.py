"""
Irrelevant job repository for tracking AI-filtered jobs
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.models import IrrelevantJob
from app.db.repositories.base import BaseRepository


class IrrelevantJobRepository(BaseRepository[IrrelevantJob]):
    """Repository for IrrelevantJob model"""

    def __init__(self, db: Session):
        super().__init__(IrrelevantJob, db)

    def add(self, url: str) -> IrrelevantJob:
        """
        Add a URL to the irrelevant jobs cache.

        Args:
            url: Job URL that was filtered as irrelevant

        Returns:
            IrrelevantJob object
        """
        # Check if already exists
        existing = self.get_by_url(url)
        if existing:
            return existing

        # Create new entry
        return self.create({"url": url})

    def get_by_url(self, url: str) -> Optional[IrrelevantJob]:
        """Get irrelevant job by URL"""
        return self.db.query(IrrelevantJob).filter(IrrelevantJob.url == url).first()

    def exists_by_url(self, url: str) -> bool:
        """Check if URL is in irrelevant jobs cache"""
        return self.get_by_url(url) is not None

    def remove(self, url: str) -> bool:
        """
        Remove a URL from irrelevant jobs cache.
        Useful if a job was incorrectly filtered.

        Args:
            url: Job URL to remove

        Returns:
            True if removed, False if not found
        """
        irrelevant = self.get_by_url(url)
        if irrelevant:
            self.db.delete(irrelevant)
            self.db.commit()
            return True
        return False

    def get_all_urls(self) -> List[str]:
        """Get all irrelevant job URLs"""
        return [job.url for job in self.db.query(IrrelevantJob).all()]

    def clear_all(self) -> int:
        """
        Clear all irrelevant jobs (use with caution!).

        Returns:
            Number of entries deleted
        """
        count = self.db.query(IrrelevantJob).count()
        self.db.query(IrrelevantJob).delete()
        self.db.commit()
        return count
