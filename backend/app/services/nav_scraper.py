"""
NAV API Scraper Service
Scrapes tech job listings from NAV.no using the official API
"""

import httpx
from typing import List, Dict, Optional
from datetime import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class NAVScraper:
    """Scraper for NAV.no job listings using official API"""

    BASE_URL = "https://pam-stilling-feed.nav.no/api/v1"
    PUBLIC_TOKEN_URL = "https://pam-stilling-feed.nav.no/api/publicToken"

    def __init__(self, api_token: str = None):
        """
        Initialize NAV scraper

        Args:
            api_token: JWT token for API access (optional, will fetch public token if not provided)
        """
        self.api_token = api_token or settings.nav_api_token
        self.headers = {
            'Accept': 'application/json',
        }

    async def get_public_token(self) -> Optional[str]:
        """
        Fetch public token from NAV API

        Returns:
            JWT token string or None if fetch fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.PUBLIC_TOKEN_URL)
                response.raise_for_status()
                # Token is in plain text response
                token = response.text.strip().split('\n')[-1]  # Last line is the token
                logger.info("Successfully fetched public NAV API token")
                return token
        except Exception as e:
            logger.error(f"Error fetching public token: {e}")
            return None

    async def fetch_feed(self, feed_id: str = None, etag: str = None, last: bool = True) -> Optional[Dict]:
        """
        Fetch a feed page from NAV API

        Args:
            feed_id: Specific feed ID to fetch (optional, fetches latest if None)
            etag: ETag for conditional request (returns 304 if not modified)
            last: If True, fetch the newest page instead of first page (default True)

        Returns:
            Feed dictionary or None if fetch fails
        """
        # Ensure we have a token
        if not self.api_token:
            self.api_token = await self.get_public_token()
            if not self.api_token:
                logger.error("No API token available")
                return None

        headers = {
            **self.headers,
            'Authorization': f'Bearer {self.api_token}'
        }

        if etag:
            headers['If-None-Match'] = etag

        url = f"{self.BASE_URL}/feed"
        if feed_id:
            url = f"{self.BASE_URL}/feed/{feed_id}"
        elif last:
            # Fetch the newest page by default
            url = f"{self.BASE_URL}/feed?last=true"

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 304:
                    logger.info("Feed not modified since last fetch (ETag match)")
                    return {'not_modified': True}

                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching NAV feed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching NAV feed: {e}")
            return None

    async def fetch_job_entry(self, uuid: str) -> Optional[Dict]:
        """
        Fetch detailed job entry from NAV API

        Args:
            uuid: Job UUID

        Returns:
            Job entry dictionary or None if fetch fails
        """
        if not self.api_token:
            self.api_token = await self.get_public_token()
            if not self.api_token:
                return None

        headers = {
            **self.headers,
            'Authorization': f'Bearer {self.api_token}'
        }

        url = f"{self.BASE_URL}/feedentry/{uuid}"

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching NAV job entry {uuid}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching NAV job entry {uuid}: {e}")
            return None

    def filter_by_location(self, job: Dict) -> bool:
        """
        Filter job by location (municipality/county)

        Args:
            job: Job dictionary from feed

        Returns:
            True if job matches location filter
        """
        feed_entry = job.get('_feed_entry', {})
        municipal = feed_entry.get('municipal', '').upper()
        county = feed_entry.get('county', '').upper()

        target_municipal = settings.nav_municipal.upper()
        target_county = settings.nav_county.upper()

        # Extract just the city name from VESTLAND.BERGEN format
        # The feed uses simple names like "BERGEN", not "VESTLAND.BERGEN"
        if '.' in target_municipal:
            target_city = target_municipal.split('.')[-1]  # Get "BERGEN" from "VESTLAND.BERGEN"
        else:
            target_city = target_municipal

        # Match if municipal matches the city name or county
        return municipal == target_city or municipal == target_municipal or county == target_county

    def filter_by_keywords(self, job: Dict, keywords: List[str]) -> Optional[str]:
        """
        Check if job matches any of the keywords

        Args:
            job: Job dictionary
            keywords: List of keywords to match

        Returns:
            Matching keyword or None
        """
        title = job.get('title', '').lower()
        description = job.get('adText', '').lower() if 'adText' in job else ''

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in title or keyword_lower in description:
                return keyword

        return None

    def parse_job(self, feed_item: Dict, job_entry: Dict = None, keyword: str = None) -> Optional[Dict]:
        """
        Parse job from NAV API response

        Args:
            feed_item: Item from feed page
            job_entry: Detailed job entry (optional)
            keyword: Keyword that matched this job (optional)

        Returns:
            Parsed job dictionary or None
        """
        try:
            feed_entry = feed_item.get('_feed_entry', {})
            uuid = feed_entry.get('uuid') or feed_item.get('id')

            # Basic info from feed
            title = feed_item.get('title') or feed_entry.get('title')
            company = feed_entry.get('businessName', 'Unknown')
            municipal = feed_entry.get('municipal', '')
            status = feed_entry.get('status', 'ACTIVE')

            # URL to job posting
            url = f"https://arbeidsplassen.nav.no/stillinger/stilling/{uuid}"

            # Detailed info from entry (if available)
            description = None
            job_type = None
            deadline = None
            published = None

            if job_entry:
                description = job_entry.get('adText') or job_entry.get('description')
                properties = job_entry.get('properties', {})
                job_type = properties.get('extent')
                published = job_entry.get('published')
                deadline = job_entry.get('applicationDue')

            return {
                'title': title,
                'company': company,
                'location': municipal,
                'url': url,
                'source': 'NAV',
                'keywords': keyword,
                'deadline': deadline,
                'job_type': job_type,
                'published': published,
                'description': description,
                'summary': None,  # Will be generated by AI service
                'scraped_date': datetime.now(),
                'external_id': uuid,
                'status': status,
            }

        except Exception as e:
            logger.error(f"Error parsing NAV job: {e}")
            return None

    async def scrape_all_keywords(
        self,
        keywords: List[str] = None,
        limit: int = None,
        last_etag: str = None
    ) -> tuple[List[Dict], Optional[str]]:
        """
        Scrape NAV jobs for all keywords

        Args:
            keywords: List of keywords to search (default from settings)
            limit: Maximum total jobs to fetch (optional)
            last_etag: ETag from last fetch for incremental sync

        Returns:
            Tuple of (list of jobs, new_etag)
        """
        keywords = keywords or settings.get_keywords()
        all_jobs = []
        new_etag = None

        logger.info(f"Starting NAV scraping with {len(keywords)} keywords")

        # Fetch the feed
        feed_data = await self.fetch_feed(etag=last_etag)

        if not feed_data:
            logger.error("Failed to fetch NAV feed")
            return [], None

        if feed_data.get('not_modified'):
            logger.info("NAV feed not modified since last fetch")
            return [], last_etag

        # Process feed items
        items = feed_data.get('items', [])
        logger.info(f"Processing {len(items)} items from NAV feed")

        # Debug: Log location data from first few items
        if items:
            logger.info("=== DEBUG: Checking location data in feed items ===")
            for i, item in enumerate(items[:5]):
                feed_entry = item.get('_feed_entry', {})
                logger.info(f"Item {i+1}: municipal={feed_entry.get('municipal')}, county={feed_entry.get('county')}, status={feed_entry.get('status')}")
            logger.info("=== END DEBUG ===")

        location_passed = 0
        status_passed = 0
        keyword_passed = 0

        for item in items:
            # Filter by location
            if not self.filter_by_location(item):
                continue
            location_passed += 1

            # Filter by status - only ACTIVE jobs (check feed_entry status)
            feed_entry = item.get('_feed_entry', {})
            if feed_entry.get('status') != 'ACTIVE':
                continue
            status_passed += 1

            # Fetch full job details
            uuid = feed_entry.get('uuid') or item.get('id')
            job_entry = await self.fetch_job_entry(uuid)

            if not job_entry:
                continue

            # Filter by keywords
            matched_keyword = self.filter_by_keywords(job_entry, keywords)
            if not matched_keyword:
                continue
            keyword_passed += 1

            # Parse job
            job = self.parse_job(item, job_entry, matched_keyword)
            if job:
                all_jobs.append(job)

            # Check limit
            if limit and len(all_jobs) >= limit:
                break

            # Rate limiting
            if settings.request_delay > 0:
                import asyncio
                await asyncio.sleep(settings.request_delay)

        # Get new ETag for next fetch (TODO: implement ETag extraction)
        # new_etag = response headers would have ETag

        logger.info(f"=== NAV Filter Results ===")
        logger.info(f"Total items: {len(items)}")
        logger.info(f"Passed location filter: {location_passed}")
        logger.info(f"Passed status filter: {status_passed}")
        logger.info(f"Passed keyword filter: {keyword_passed}")
        logger.info(f"Final jobs scraped: {len(all_jobs)}")
        logger.info(f"=========================")

        return all_jobs, new_etag
