#!/usr/bin/env python
"""
Development server runner
Start the FastAPI application for local testing
"""

import uvicorn
from app.utils.logging import setup_logging

# Set up logging
logger = setup_logging()

if __name__ == "__main__":
    logger.info("Starting Job Scraper API development server...")
    logger.info("API Documentation: http://localhost:8000/docs")
    logger.info("Alternative docs: http://localhost:8000/redoc")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
