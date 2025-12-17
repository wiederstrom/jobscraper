"""
Pydantic schemas for Job endpoints
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class JobBase(BaseModel):
    """Base Job schema with common fields"""
    title: str
    company: str
    location: Optional[str] = None
    url: str
    source: str  # 'FINN' or 'NAV'
    keywords: Optional[str] = None
    deadline: Optional[str] = None
    job_type: Optional[str] = None
    published: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None


class JobCreate(JobBase):
    """Schema for creating a new job"""
    scraped_date: Optional[datetime] = None
    external_id: Optional[str] = None
    status: str = "ACTIVE"


class JobUpdate(BaseModel):
    """Schema for updating job metadata (user interactions)"""
    is_favorite: Optional[bool] = None
    is_hidden: Optional[bool] = None
    applied: Optional[bool] = None
    notes: Optional[str] = None


class JobResponse(JobBase):
    """Schema for job responses"""
    id: int
    scraped_date: datetime
    is_hidden: bool
    is_favorite: bool
    applied: bool
    applied_date: Optional[datetime] = None
    notes: Optional[str] = None
    last_checked: Optional[datetime] = None
    external_id: Optional[str] = None
    status: str
    expire_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobListResponse(BaseModel):
    """Schema for paginated job list"""
    jobs: list[JobResponse]
    total: int
    skip: int
    limit: int


class JobFilters(BaseModel):
    """Schema for job filtering parameters"""
    source: Optional[str] = Field(None, description="Filter by source (FINN or NAV)")
    keyword: Optional[str] = Field(None, description="Filter by keyword")
    search: Optional[str] = Field(None, description="Search in title, company, description")
    is_favorite: Optional[bool] = Field(None, description="Filter by favorite status")
    is_hidden: Optional[bool] = Field(False, description="Include hidden jobs")
    applied: Optional[bool] = Field(None, description="Filter by applied status")
    status: Optional[str] = Field(None, description="Filter by status (ACTIVE, INACTIVE, EXPIRED)")
    skip: int = Field(0, ge=0, description="Pagination offset")
    limit: int = Field(100, ge=1, le=1000, description="Pagination limit")
