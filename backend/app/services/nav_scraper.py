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

    async def fetch_feed(self, feed_id: str = None, etag: str = None, last: bool = True, modified_since: str = None) -> Optional[Dict]:
        """
        Fetch a feed page from NAV API

        Args:
            feed_id: Specific feed ID to fetch (optional, fetches latest if None)
            etag: ETag for conditional request (returns 304 if not modified)
            last: If True, fetch the newest page instead of first page (default True)
            modified_since: RFC 1123 datetime string to fetch only jobs modified after this date

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

        if modified_since:
            headers['If-Modified-Since'] = modified_since

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
            job: Job entry dictionary (with ad_content)
            keywords: List of keywords to match

        Returns:
            Matching keyword or None
        """
        # Get data from ad_content
        ad_content = job.get('ad_content', {})
        title = ad_content.get('title', '').lower()
        description = ad_content.get('description', '').lower()

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
                # The actual data is nested in 'ad_content'
                ad_content = job_entry.get('ad_content', {})

                # Get title from ad_content (more reliable than feed)
                if ad_content.get('title'):
                    title = ad_content.get('title')

                description = ad_content.get('description')
                properties = ad_content.get('properties', {})
                job_type = properties.get('extent')
                published = ad_content.get('published')
                deadline = ad_content.get('applicationDue')

                # Get location from workLocations
                work_locations = ad_content.get('workLocations', [])
                if work_locations:
                    municipal = work_locations[0].get('municipal', municipal)

                # Get company/employer from ad_content
                employer = ad_content.get('employer', {})
                if employer and employer.get('name'):
                    company = employer.get('name')

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
        last_etag: str = None,
        max_pages: int = 10
    ) -> tuple[List[Dict], Optional[str]]:
        """
        Scrape NAV jobs for all keywords

        Args:
            keywords: List of keywords to search (default from settings)
            limit: Maximum total jobs to fetch (optional)
            last_etag: ETag from last fetch for incremental sync
            max_pages: Maximum number of feed pages to process (default 10)

        Returns:
            Tuple of (list of jobs, new_etag)
        """
        keywords = keywords or settings.get_keywords()
        all_jobs = []
        new_etag = None

        logger.info(f"Starting NAV scraping with {len(keywords)} keywords, max_pages={max_pages}")

        # Use If-Modified-Since to get jobs from the last 30 days
        from datetime import datetime, timedelta
        since_date = datetime.now() - timedelta(days=30)
        # RFC 1123 format: "Sun, 01 Dec 2024 00:00:00 GMT"
        modified_since = since_date.strftime('%a, %d %b %Y %H:%M:%S GMT')
        logger.info(f"Fetching jobs modified since: {modified_since}")

        # Start from first page with date filter
        feed_data = await self.fetch_feed(last=False, etag=last_etag, modified_since=modified_since)

        if not feed_data:
            logger.error("Failed to fetch NAV feed")
            return [], None

        if feed_data.get('not_modified'):
            logger.info("NAV feed not modified since last fetch")
            return [], last_etag

        # Process pages one by one
        pages_processed = 0
        current_feed = feed_data

        while current_feed and pages_processed < max_pages:
            items = current_feed.get('items', [])
            logger.info(f"Processing page {pages_processed + 1}: {len(items)} items")

            # Process items in this page
            all_jobs.extend(await self._process_feed_items(items, keywords, limit, len(all_jobs)))

            # Check if we've hit the limit
            if limit and len(all_jobs) >= limit:
                break

            # Get next page
            next_id = current_feed.get('next_id')
            if not next_id:
                logger.info("Reached end of feed (no more pages)")
                break

            pages_processed += 1
            current_feed = await self.fetch_feed(feed_id=next_id, last=False)

            # Rate limiting between pages
            if settings.request_delay > 0:
                import asyncio
                await asyncio.sleep(settings.request_delay)

        logger.info(f"Processed {pages_processed + 1} pages, found {len(all_jobs)} matching jobs")
        return all_jobs, new_etag

    async def _process_feed_items(
        self,
        items: List[Dict],
        keywords: List[str],
        limit: Optional[int],
        current_count: int
    ) -> List[Dict]:
        """
        Process items from a feed page

        Args:
            items: List of feed items
            keywords: Keywords to match
            limit: Maximum total jobs
            current_count: Current number of jobs already collected

        Returns:
            List of processed jobs
        """
        jobs = []
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
                jobs.append(job)

            # Check limit
            if limit and (current_count + len(jobs)) >= limit:
                break

            # Rate limiting
            if settings.request_delay > 0:
                import asyncio
                await asyncio.sleep(settings.request_delay)

        logger.info(f"Page results: {len(items)} items -> {location_passed} location -> {status_passed} active -> {keyword_passed} keywords -> {len(jobs)} jobs")
        return jobs
