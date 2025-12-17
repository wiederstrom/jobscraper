"""
API v1 router - aggregates all v1 endpoints
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, jobs, stats

# Create API v1 router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(jobs.router, tags=["Jobs"])
api_router.include_router(stats.router, tags=["Statistics"])
