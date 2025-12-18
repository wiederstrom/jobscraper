"""
Job Scheduler Service
Manages background scraping jobs using APScheduler
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging

from app.db.session import SessionLocal
from app.services.job_manager import JobManager

logger = logging.getLogger(__name__)


class JobScheduler:
    """Manages scheduled background jobs for scraping"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def scrape_finn_job(self):
        """Scheduled job to scrape FINN.no"""
        logger.info("="*60)
        logger.info(f"Starting scheduled FINN scraping job at {datetime.now()}")
        logger.info("="*60)

        db = SessionLocal()
        try:
            manager = JobManager(db)
            stats = await manager.scrape_finn_jobs()

            logger.info("FINN scraping completed!")
            logger.info(f"Stats: {stats}")

        except Exception as e:
            logger.error(f"Error in scheduled FINN scraping: {e}", exc_info=True)
        finally:
            db.close()

    async def scrape_nav_job(self):
        """Scheduled job to scrape NAV.no"""
        logger.info("="*60)
        logger.info(f"Starting scheduled NAV scraping job at {datetime.now()}")
        logger.info("="*60)

        db = SessionLocal()
        try:
            manager = JobManager(db)
            stats = await manager.scrape_nav_jobs()

            logger.info("NAV scraping completed!")
            logger.info(f"Stats: {stats}")

        except Exception as e:
            logger.error(f"Error in scheduled NAV scraping: {e}", exc_info=True)
        finally:
            db.close()

    async def cleanup_inactive_job(self):
        """Scheduled job to clean up inactive jobs"""
        logger.info("="*60)
        logger.info(f"Starting cleanup job at {datetime.now()}")
        logger.info("="*60)

        db = SessionLocal()
        try:
            manager = JobManager(db)
            count = await manager.cleanup_inactive_jobs(days_threshold=30)

            logger.info(f"Cleanup completed! Marked {count} jobs as inactive")

        except Exception as e:
            logger.error(f"Error in cleanup job: {e}", exc_info=True)
        finally:
            db.close()

    def setup_jobs(self):
        """Set up all scheduled jobs"""

        # FINN scraping - twice daily at 8 AM and 6 PM
        self.scheduler.add_job(
            self.scrape_finn_job,
            trigger=CronTrigger(hour='8,18', minute=0),
            id='scrape_finn',
            name='Scrape FINN.no jobs',
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
        )
        logger.info("Added job: Scrape FINN.no (8 AM, 6 PM daily)")

        # NAV scraping - twice daily at 9 AM and 7 PM (offset from FINN)
        self.scheduler.add_job(
            self.scrape_nav_job,
            trigger=CronTrigger(hour='9,19', minute=0),
            id='scrape_nav',
            name='Scrape NAV.no jobs',
            replace_existing=True,
            max_instances=1,
        )
        logger.info("Added job: Scrape NAV.no (9 AM, 7 PM daily)")

        # Cleanup inactive jobs - once daily at 3 AM
        self.scheduler.add_job(
            self.cleanup_inactive_job,
            trigger=CronTrigger(hour=3, minute=0),
            id='cleanup_inactive',
            name='Clean up inactive jobs',
            replace_existing=True,
            max_instances=1,
        )
        logger.info("Added job: Cleanup inactive jobs (3 AM daily)")

    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            self.setup_jobs()
            self.scheduler.start()
            self.is_running = True
            logger.info("Job scheduler started")
            logger.info(f"Scheduler timezone: {self.scheduler.timezone}")
            self.print_jobs()

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.is_running:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Job scheduler shut down")

    def print_jobs(self):
        """Print all scheduled jobs"""
        jobs = self.scheduler.get_jobs()
        if jobs:
            logger.info("Scheduled jobs:")
            for job in jobs:
                logger.info(f"  - {job.name} (ID: {job.id}) - Next run: {job.next_run_time}")
        else:
            logger.info("No scheduled jobs")

    def trigger_job(self, job_id: str):
        """Manually trigger a job by ID"""
        job = self.scheduler.get_job(job_id)
        if job:
            logger.info(f"Manually triggering job: {job_id}")
            job.modify(next_run_time=datetime.now())
            return True
        else:
            logger.warning(f"Job not found: {job_id}")
            return False

    def pause_job(self, job_id: str):
        """Pause a scheduled job"""
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True
        return False

    def resume_job(self, job_id: str):
        """Resume a paused job"""
        job = self.scheduler.get_job(job_id)
        if job:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
            return True
        return False

    def get_job_status(self) -> dict:
        """Get status of all scheduled jobs"""
        jobs = self.scheduler.get_jobs()
        return {
            'scheduler_running': self.is_running,
            'jobs': [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger),
                }
                for job in jobs
            ]
        }


# Global scheduler instance
scheduler = JobScheduler()
