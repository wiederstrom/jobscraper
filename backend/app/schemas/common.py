"""
Common Pydantic schemas
"""

from typing import Optional, Any
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    error_code: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response"""
    message: str
    data: Optional[Any] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    ai_enabled: bool
    timestamp: str


class PaginationParams(BaseModel):
    """Pagination parameters"""
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of records to return")
