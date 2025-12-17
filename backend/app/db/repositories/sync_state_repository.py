"""
Sync state repository for tracking scraper synchronization
"""

from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import SyncState
from app.db.repositories.base import BaseRepository


class SyncStateRepository(BaseRepository[SyncState]):
    """Repository for SyncState model"""

    def __init__(self, db: Session):
        super().__init__(SyncState, db)

    def get_by_source(self, source: str) -> Optional[SyncState]:
        """
        Get sync state by source name.

        Args:
            source: Source name ('FINN' or 'NAV')

        Returns:
            SyncState object or None
        """
        return self.db.query(SyncState).filter(SyncState.source == source).first()

    def update_sync_state(
        self,
        source: str,
        last_sync: Optional[datetime] = None,
        last_etag: Optional[str] = None,
        jobs_added: Optional[int] = None,
        jobs_removed: Optional[int] = None,
    ) -> SyncState:
        """
        Update or create sync state for a source.

        Args:
            source: Source name ('FINN' or 'NAV')
            last_sync: Last synchronization timestamp
            last_etag: ETag from last API response (NAV only)
            jobs_added: Number of jobs added in last run
            jobs_removed: Number of jobs removed in last run

        Returns:
            Updated or created SyncState object
        """
        sync_state = self.get_by_source(source)

        if sync_state:
            # Update existing
            updates = {}
            if last_sync is not None:
                updates["last_sync"] = last_sync
            if last_etag is not None:
                updates["last_etag"] = last_etag
            if jobs_added is not None:
                updates["jobs_added_last_run"] = jobs_added
            if jobs_removed is not None:
                updates["jobs_removed_last_run"] = jobs_removed

            return self.update(sync_state, updates)
        else:
            # Create new
            return self.create({
                "source": source,
                "last_sync": last_sync or datetime.now(),
                "last_etag": last_etag,
                "jobs_added_last_run": jobs_added or 0,
                "jobs_removed_last_run": jobs_removed or 0,
            })

    def get_last_sync_time(self, source: str) -> Optional[datetime]:
        """
        Get the last sync timestamp for a source.

        Args:
            source: Source name

        Returns:
            Last sync datetime or None if never synced
        """
        sync_state = self.get_by_source(source)
        return sync_state.last_sync if sync_state else None

    def get_last_etag(self, source: str) -> Optional[str]:
        """
        Get the last ETag for a source (used for NAV API).

        Args:
            source: Source name

        Returns:
            Last ETag or None
        """
        sync_state = self.get_by_source(source)
        return sync_state.last_etag if sync_state else None

    def record_scrape_result(
        self,
        source: str,
        jobs_added: int,
        jobs_removed: int = 0,
        etag: Optional[str] = None,
    ) -> SyncState:
        """
        Record the result of a scraping run.

        Args:
            source: Source name
            jobs_added: Number of new jobs added
            jobs_removed: Number of jobs removed/marked inactive
            etag: ETag from API response (for NAV)

        Returns:
            Updated SyncState object
        """
        return self.update_sync_state(
            source=source,
            last_sync=datetime.now(),
            last_etag=etag,
            jobs_added=jobs_added,
            jobs_removed=jobs_removed,
        )
