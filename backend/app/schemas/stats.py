"""
Pydantic schemas for statistics endpoints
"""

from pydantic import BaseModel


class SourceStats(BaseModel):
    """Statistics by source"""
    FINN: int
    NAV: int


class StatusStats(BaseModel):
    """Statistics by status"""
    ACTIVE: int
    INACTIVE: int
    EXPIRED: int


class JobStatistics(BaseModel):
    """Overall job statistics"""
    total_jobs: int
    favorites: int
    applied: int
    sources: SourceStats
    status: StatusStats
    new_last_7_days: int
