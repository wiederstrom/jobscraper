"""
Main FastAPI application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.utils.logging import setup_logging


# Set up logging
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup
    logger.info("Starting Job Scraper API...")
    logger.info(f"Database URL: {settings.database_url[:30]}...")
    logger.info(f"AI Features - Summarization: {settings.enable_summarization}, Filter: {settings.enable_ai_filter}")

    yield

    # Shutdown
    logger.info("Shutting down Job Scraper API...")


# Create FastAPI application
app = FastAPI(
    title="Job Scraper API",
    description="Norwegian job scraper for FINN.no and NAV.no with AI-powered filtering",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Job Scraper API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "ai_enabled": settings.enable_summarization or settings.enable_ai_filter
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
