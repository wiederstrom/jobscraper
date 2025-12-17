"""
Statistics endpoints
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.dependencies import get_db
from app.db.repositories.job_repository import JobRepository
from app.schemas.stats import JobStatistics, SourceStats, StatusStats

router = APIRouter()


@router.get("/stats", response_model=JobStatistics, tags=["Statistics"])
async def get_statistics(
    source: Optional[str] = Query(None, description="Filter by source"),
    is_hidden: bool = Query(False, description="Include hidden jobs"),
    db: Session = Depends(get_db),
):
    """
    Get job statistics.

    Returns:
    - Total number of jobs
    - Number of favorites
    - Number of applied jobs
    - Breakdown by source (FINN vs NAV)
    - Breakdown by status (ACTIVE vs INACTIVE)
    - New jobs in last 7 days

    Can be filtered by source to get source-specific stats.
    """
    repo = JobRepository(db)

    stats_data = repo.get_statistics(source=source, is_hidden=is_hidden)

    return JobStatistics(
        total_jobs=stats_data["total_jobs"],
        favorites=stats_data["favorites"],
        applied=stats_data["applied"],
        sources=SourceStats(**stats_data["sources"]),
        status=StatusStats(**stats_data["status"]),
        new_last_7_days=stats_data["new_last_7_days"]
    )
