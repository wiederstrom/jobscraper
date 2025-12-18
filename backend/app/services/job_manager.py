"""
Job Manager Service
Orchestrates job scraping, AI filtering, and database storage
"""

from typing import List, Dict
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.services.finn_scraper import FINNScraper
from app.services.nav_scraper import NAVScraper
from app.services.ai_service import AIService
from app.db.repositories.job_repository import JobRepository
from app.db.repositories.irrelevant_repository import IrrelevantJobRepository
from app.db.repositories.sync_state_repository import SyncStateRepository

logger = logging.getLogger(__name__)


class JobManager:
    """Manages the job scraping and storage pipeline"""

    def __init__(self, db: Session):
        self.db = db
        self.finn_scraper = FINNScraper()
        self.nav_scraper = NAVScraper()
        self.ai_service = AIService()
        self.job_repo = JobRepository(db)
        self.irrelevant_repo = IrrelevantJobRepository(db)
        self.sync_state_repo = SyncStateRepository(db)

    async def scrape_finn_jobs(self, keywords: List[str] = None) -> Dict[str, int]:
        """
        Scrape jobs from FINN.no, filter with AI, and store in database

        Args:
            keywords: List of keywords to search (optional, uses default from settings)

        Returns:
            Dictionary with scraping statistics
        """
        stats = {
            'jobs_scraped': 0,
            'jobs_added': 0,
            'jobs_filtered': 0,
            'jobs_duplicate': 0,
            'errors': 0,
        }

        logger.info("Starting FINN.no scraping job")
        start_time = datetime.now()

        try:
            # Scrape jobs from FINN.no
            scraped_jobs = await self.finn_scraper.scrape_all_keywords(keywords)
            stats['jobs_scraped'] = len(scraped_jobs)

            logger.info(f"Scraped {stats['jobs_scraped']} jobs from FINN.no")

            # Process each job
            for job_data in scraped_jobs:
                try:
                    # Check if already in irrelevant cache
                    if self.irrelevant_repo.exists_by_url(job_data['url']):
                        stats['jobs_filtered'] += 1
                        continue

                    # Check if already exists in database
                    if self.job_repo.exists_by_url(job_data['url']):
                        stats['jobs_duplicate'] += 1
                        continue

                    # Fetch full job details
                    details = await self.finn_scraper.fetch_job_details(job_data['url'])
                    if details:
                        job_data.update(details)

                    # AI filtering (if enabled)
                    if self.ai_service.is_enabled() and job_data.get('description'):
                        is_relevant, explanation = await self.ai_service.filter_job(
                            title=job_data['title'],
                            company=job_data['company'],
                            description=job_data['description'] or "",
                            keywords=job_data['keywords']
                        )

                        if not is_relevant:
                            # Add to irrelevant cache
                            self.irrelevant_repo.add(
                                url=job_data['url'],
                                reason=explanation
                            )
                            stats['jobs_filtered'] += 1
                            logger.info(f"Filtered out: {job_data['title']}")
                            continue

                        # Generate summary (if enabled)
                        summary = await self.ai_service.generate_summary(
                            title=job_data['title'],
                            description=job_data['description'] or ""
                        )
                        if summary:
                            job_data['summary'] = summary

                    # Add to database
                    self.job_repo.create(job_data)
                    stats['jobs_added'] += 1
                    logger.info(f"Added job: {job_data['title']}")

                except Exception as e:
                    logger.error(f"Error processing job: {e}")
                    stats['errors'] += 1
                    continue

            # Commit all changes
            self.db.commit()

            # Update sync state
            self.sync_state_repo.update_sync_state(
                source='FINN',
                last_sync=datetime.now(),
                jobs_added=stats['jobs_added']
            )
            self.db.commit()

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"FINN scraping completed in {duration:.2f}s: {stats}")

        except Exception as e:
            logger.error(f"Error in FINN scraping job: {e}")
            self.db.rollback()
            raise

        return stats

    async def scrape_nav_jobs(self, keywords: List[str] = None) -> Dict[str, int]:
        """
        Scrape jobs from NAV.no using official API, filter with AI, and store in database

        Args:
            keywords: List of keywords to search (optional, uses default from settings)

        Returns:
            Dictionary with scraping statistics
        """
        stats = {
            'jobs_scraped': 0,
            'jobs_added': 0,
            'jobs_filtered': 0,
            'jobs_duplicate': 0,
            'errors': 0,
        }

        logger.info("Starting NAV.no scraping job")
        start_time = datetime.now()

        try:
            # Get last ETag for incremental sync
            nav_sync = self.sync_state_repo.get_by_source('NAV')
            last_etag = nav_sync.last_etag if nav_sync else None

            # Scrape jobs from NAV API
            scraped_jobs, new_etag = await self.nav_scraper.scrape_all_keywords(
                keywords,
                last_etag=last_etag
            )
            stats['jobs_scraped'] = len(scraped_jobs)

            logger.info(f"Scraped {stats['jobs_scraped']} jobs from NAV API")

            # Process each job
            for job_data in scraped_jobs:
                try:
                    # Check if already in irrelevant cache
                    if self.irrelevant_repo.exists_by_url(job_data['url']):
                        stats['jobs_filtered'] += 1
                        continue

                    # Check if already exists in database
                    if self.job_repo.exists_by_url(job_data['url']):
                        stats['jobs_duplicate'] += 1
                        continue

                    # AI filtering (if enabled)
                    if self.ai_service.is_enabled() and job_data.get('description'):
                        is_relevant, explanation = await self.ai_service.filter_job(
                            title=job_data['title'],
                            company=job_data['company'],
                            description=job_data['description'] or "",
                            keywords=job_data['keywords']
                        )

                        if not is_relevant:
                            # Add to irrelevant cache
                            self.irrelevant_repo.add(
                                url=job_data['url'],
                                reason=explanation
                            )
                            stats['jobs_filtered'] += 1
                            logger.info(f"Filtered out: {job_data['title']}")
                            continue

                        # Generate summary (if enabled)
                        summary = await self.ai_service.generate_summary(
                            title=job_data['title'],
                            description=job_data['description'] or ""
                        )
                        if summary:
                            job_data['summary'] = summary

                    # Add to database
                    self.job_repo.create(job_data)
                    stats['jobs_added'] += 1
                    logger.info(f"Added job: {job_data['title']}")

                except Exception as e:
                    logger.error(f"Error processing job: {e}")
                    stats['errors'] += 1
                    continue

            # Commit all changes
            self.db.commit()

            # Update sync state
            self.sync_state_repo.update_sync_state(
                source='NAV',
                last_sync=datetime.now(),
                last_etag=new_etag,
                jobs_added=stats['jobs_added']
            )
            self.db.commit()

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"NAV scraping completed in {duration:.2f}s: {stats}")

        except Exception as e:
            logger.error(f"Error in NAV scraping job: {e}")
            self.db.rollback()
            raise

        return stats

    async def cleanup_inactive_jobs(self, days_threshold: int = 30) -> int:
        """
        Mark jobs as inactive if they haven't been checked in X days

        Args:
            days_threshold: Number of days before marking as inactive

        Returns:
            Number of jobs marked as inactive
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days_threshold)

        # Find jobs that haven't been updated recently
        jobs = self.job_repo.db.query(self.job_repo.model).filter(
            self.job_repo.model.last_checked < cutoff_date,
            self.job_repo.model.status == 'ACTIVE'
        ).all()

        job_ids = [job.id for job in jobs]
        count = self.job_repo.mark_as_inactive(job_ids)

        self.db.commit()
        logger.info(f"Marked {count} jobs as inactive (not checked in {days_threshold} days)")

        return count

    def get_scraping_stats(self) -> Dict:
        """
        Get statistics about scraping activity

        Returns:
            Dictionary with scraping stats
        """
        finn_sync = self.sync_state_repo.get_by_source('FINN')
        nav_sync = self.sync_state_repo.get_by_source('NAV')

        return {
            'finn': {
                'last_sync': finn_sync.last_sync.isoformat() if finn_sync and finn_sync.last_sync else None,
                'jobs_added': finn_sync.jobs_added if finn_sync else 0,
            },
            'nav': {
                'last_sync': nav_sync.last_sync.isoformat() if nav_sync and nav_sync.last_sync else None,
                'jobs_added': nav_sync.jobs_added if nav_sync else 0,
            }
        }
