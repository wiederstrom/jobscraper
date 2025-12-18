"""
Manual NAV.no Scraping Script
Run this to manually trigger a NAV API scraping job
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.services.job_manager import JobManager
from app.utils.logging import setup_logging

logger = setup_logging()


async def main():
    """Run NAV scraping job"""
    logger.info("="*60)
    logger.info("Starting manual NAV.no API scraping job")
    logger.info("="*60)

    db = SessionLocal()
    try:
        manager = JobManager(db)
        stats = await manager.scrape_nav_jobs()

        logger.info("="*60)
        logger.info("Scraping completed!")
        logger.info(f"Jobs scraped: {stats['jobs_scraped']}")
        logger.info(f"Jobs added: {stats['jobs_added']}")
        logger.info(f"Jobs filtered (AI): {stats['jobs_filtered']}")
        logger.info(f"Jobs duplicate: {stats['jobs_duplicate']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
