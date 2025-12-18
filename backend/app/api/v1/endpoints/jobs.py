"""
Job endpoints for CRUD operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.dependencies import get_db
from app.db.repositories.job_repository import JobRepository
from app.schemas.job import JobResponse, JobUpdate, JobListResponse
from app.schemas.common import SuccessResponse

router = APIRouter()


@router.get("/jobs", response_model=JobListResponse, tags=["Jobs"])
async def get_jobs(
    source: Optional[str] = Query(None, description="Filter by source (FINN or NAV)"),
    keyword: Optional[str] = Query(None, description="Filter by keyword"),
    search: Optional[str] = Query(None, description="Search in title, company, description"),
    is_favorite: Optional[bool] = Query(None, description="Filter by favorite status"),
    is_hidden: Optional[bool] = Query(False, description="Include hidden jobs"),
    applied: Optional[bool] = Query(None, description="Filter by applied status"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_range: Optional[str] = Query(None, description="Filter by date range (7days, 30days, 3months, all)"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Pagination limit"),
    db: Session = Depends(get_db),
):
    """
    Get list of jobs with optional filters.

    Filters:
    - **source**: FINN or NAV
    - **keyword**: Jobs found by this keyword
    - **search**: Full-text search across title, company, description
    - **is_favorite**: Show only favorites
    - **is_hidden**: Include hidden jobs (default: False)
    - **applied**: Filter by application status
    - **status**: ACTIVE, INACTIVE, or EXPIRED

    Returns paginated results.
    """
    repo = JobRepository(db)

    jobs = repo.get_all_with_filters(
        source=source,
        keyword=keyword,
        search=search,
        is_favorite=is_favorite,
        is_hidden=is_hidden,
        applied=applied,
        status=status,
        date_range=date_range,
        skip=skip,
        limit=limit,
    )

    # Get total count for pagination
    total = repo.count()

    return JobListResponse(
        jobs=jobs,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    """
    Get a single job by ID.

    Returns full job details including description and summary.
    """
    repo = JobRepository(db)
    job = repo.get_by_id(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.patch("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def update_job(
    job_id: int,
    job_update: JobUpdate,
    db: Session = Depends(get_db),
):
    """
    Update job metadata (user interactions).

    Can update:
    - **is_favorite**: Mark as favorite
    - **is_hidden**: Hide job from listings
    - **applied**: Mark as applied (sets applied_date automatically)
    - **notes**: Add user notes

    Only updates fields that are provided in the request.
    """
    repo = JobRepository(db)

    updated_job = repo.update_job_metadata(
        job_id=job_id,
        is_favorite=job_update.is_favorite,
        is_hidden=job_update.is_hidden,
        applied=job_update.applied,
        notes=job_update.notes,
    )

    if not updated_job:
        raise HTTPException(status_code=404, detail="Job not found")

    return updated_job


@router.delete("/jobs/{job_id}", response_model=SuccessResponse, tags=["Jobs"])
async def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
):
    """
    Soft delete a job by setting is_hidden=True.

    The job remains in the database but won't appear in default listings.
    """
    repo = JobRepository(db)

    updated_job = repo.update_job_metadata(job_id=job_id, is_hidden=True)

    if not updated_job:
        raise HTTPException(status_code=404, detail="Job not found")

    return SuccessResponse(
        message="Job hidden successfully",
        data={"job_id": job_id}
    )
