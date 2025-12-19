"""
Scheduler Management API Endpoints
Provides control over background scraping jobs
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from app.services.scheduler import scheduler
from app.services.nav_scraper import NAVScraper

router = APIRouter()


@router.get("/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """
    Get status of the job scheduler and all scheduled jobs

    Returns:
        Dictionary with scheduler status and job information
    """
    return scheduler.get_job_status()


@router.post("/trigger/{job_id}")
async def trigger_job(job_id: str) -> Dict[str, str]:
    """
    Manually trigger a scheduled job to run immediately

    Args:
        job_id: ID of job to trigger (scrape_finn, scrape_nav, cleanup_inactive)

    Returns:
        Success message

    Raises:
        HTTPException: If job_id is not found
    """
    valid_jobs = ['scrape_finn', 'scrape_nav', 'cleanup_inactive']

    if job_id not in valid_jobs:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid job_id. Must be one of: {', '.join(valid_jobs)}"
        )

    success = scheduler.trigger_job(job_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )

    return {
        "message": f"Job '{job_id}' triggered successfully",
        "job_id": job_id
    }


@router.post("/pause/{job_id}")
async def pause_job(job_id: str) -> Dict[str, str]:
    """
    Pause a scheduled job

    Args:
        job_id: ID of job to pause

    Returns:
        Success message

    Raises:
        HTTPException: If job_id is not found
    """
    success = scheduler.pause_job(job_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )

    return {
        "message": f"Job '{job_id}' paused successfully",
        "job_id": job_id
    }


@router.post("/resume/{job_id}")
async def resume_job(job_id: str) -> Dict[str, str]:
    """
    Resume a paused job

    Args:
        job_id: ID of job to resume

    Returns:
        Success message

    Raises:
        HTTPException: If job_id is not found
    """
    success = scheduler.resume_job(job_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}"
        )

    return {
        "message": f"Job '{job_id}' resumed successfully",
        "job_id": job_id
    }


@router.get("/jobs")
async def list_jobs() -> Dict[str, Any]:
    """
    List all scheduled jobs with their details

    Returns:
        Dictionary with list of scheduled jobs
    """
    status = scheduler.get_job_status()
    return {
        "scheduler_running": status['scheduler_running'],
        "total_jobs": len(status['jobs']),
        "jobs": status['jobs']
    }


@router.get("/debug/nav-feed")
async def debug_nav_feed(limit: int = 10) -> Dict[str, Any]:
    """
    Debug endpoint to examine NAV feed location data

    Args:
        limit: Number of items to examine (default 10)

    Returns:
        Sample of feed items with their location data
    """
    scraper = NAVScraper()
    feed_data = await scraper.fetch_feed()

    if not feed_data:
        raise HTTPException(status_code=500, detail="Failed to fetch NAV feed")

    items = feed_data.get('items', [])
    sample_items = []

    for i, item in enumerate(items[:limit]):
        feed_entry = item.get('_feed_entry', {})
        sample_items.append({
            'index': i + 1,
            'title': item.get('title', 'No title'),
            'municipal': feed_entry.get('municipal'),
            'county': feed_entry.get('county'),
            'status': feed_entry.get('status'),
            'businessName': feed_entry.get('businessName'),
        })

    return {
        'total_items': len(items),
        'sample_count': len(sample_items),
        'sample_items': sample_items,
        'target_municipal': 'VESTLAND.BERGEN',
        'target_county': 'VESTLAND',
    }
