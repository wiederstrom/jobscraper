"""
Logging configuration for job scraper API
"""

import logging
import sys
from app.config import settings


def setup_logging():
    """Configure application logging"""

    # Get log level from settings
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set specific log levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


# Create logger instance
logger = logging.getLogger(__name__)
