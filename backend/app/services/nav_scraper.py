"""
NAV Website Scraper Service
Scrapes tech job listings from arbeidsplassen.nav.no by web scraping search results
"""

import httpx
from typing import List, Dict, Optional
from datetime import datetime
import logging
from bs4 import BeautifulSoup
import json
import re

from app.config import settings

logger = logging.getLogger(__name__)


class NAVScraper:
    """Scraper for NAV.no job listings by web scraping arbeidsplassen.nav.no"""

    BASE_URL = "https://arbeidsplassen.nav.no"
    SEARCH_URL = f"{BASE_URL}/stillinger"

    def __init__(self):
        """Initialize NAV scraper"""
        self.headers = {
            'User-Agent': settings.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,no;q=0.8',
        }

    async def search_jobs(self, keyword: str, location: str = None, limit: int = 100) -> List[Dict]:
        """
        Search for jobs on NAV website

        Args:
            keyword: Search keyword
            location: Location filter (e.g., "VESTLAND.BERGEN")
            limit: Maximum jobs to return

        Returns:
            List of job dictionaries
        """
        jobs = []

        # Build search URL with parameters
        params = {
            'q': keyword,
            'v': '5',  # Version parameter
        }

        if location:
            # Parse location like "VESTLAND.BERGEN" into county and municipal
            if '.' in location:
                county, municipal = location.split('.', 1)
                params['county'] = county
                params['municipal'] = location
            else:
                params['county'] = location

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
                response = await client.get(self.SEARCH_URL, params=params, headers=self.headers)
                response.raise_for_status()

                # Parse the HTML
                soup = BeautifulSoup(response.content, 'lxml')

                # The page contains embedded JSON data with job listings
                # Look for the Next.js data script
                scripts = soup.find_all('script', id='__NEXT_DATA__')

                if scripts:
                    data_script = scripts[0]
                    try:
                        page_data = json.loads(data_script.string)

                        # Extract job listings from the embedded data
                        props = page_data.get('props', {}).get('pageProps', {})
                        search_result = props.get('searchResult', {})
                        ads = search_result.get('ads', [])

                        logger.info(f"Found {len(ads)} jobs for keyword '{keyword}' in {location}")

                        for ad in ads[:limit]:
                            job = self._parse_job_from_data(ad, keyword)
                            if job:
                                jobs.append(job)

                    except (json.JSONDecodeError, KeyError) as e:
                        logger.error(f"Error parsing embedded job data: {e}")
                        # Fallback to HTML parsing
                        jobs = await self._parse_jobs_from_html(soup, keyword, limit)
                else:
                    # Fallback to HTML parsing
                    jobs = await self._parse_jobs_from_html(soup, keyword, limit)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error searching NAV for '{keyword}': {e}")
        except Exception as e:
            logger.error(f"Error searching NAV for '{keyword}': {e}")

        return jobs

    def _parse_job_from_data(self, ad_data: Dict, keyword: str) -> Optional[Dict]:
        """
        Parse job from embedded JSON data

        Args:
            ad_data: Ad data from embedded JSON
            keyword: Search keyword that found this job

        Returns:
            Parsed job dictionary or None
        """
        try:
            uuid = ad_data.get('uuid')
            if not uuid:
                return None

            title = ad_data.get('title', '')
            employer = ad_data.get('employer', {})
            company = employer.get('name', 'Unknown')

            # Get location
            locations = ad_data.get('locationList', [])
            location = locations[0] if locations else 'Unknown'

            # Get dates
            published = ad_data.get('published')
            expires = ad_data.get('expires')
            deadline = ad_data.get('applicationDue')

            # Get job details
            description = ad_data.get('description', '')
            properties = ad_data.get('properties', {})
            job_type = properties.get('extent')

            # Build URL
            url = f"{self.BASE_URL}/stillinger/stilling/{uuid}"

            return {
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'source': 'NAV',
                'keywords': keyword,
                'deadline': deadline,
                'job_type': job_type,
                'published': published,
                'description': description,
                'summary': None,
                'scraped_date': datetime.now(),
                'external_id': uuid,
                'status': 'ACTIVE',
            }

        except Exception as e:
            logger.error(f"Error parsing job from data: {e}")
            return None

    async def _parse_jobs_from_html(self, soup: BeautifulSoup, keyword: str, limit: int) -> List[Dict]:
        """
        Fallback: Parse jobs from HTML when JSON data is not available

        Args:
            soup: BeautifulSoup object
            keyword: Search keyword
            limit: Maximum jobs to return

        Returns:
            List of job dictionaries
        """
        jobs = []

        # Find job listing links
        job_links = soup.find_all('a', href=re.compile(r'/stillinger/stilling/'))

        logger.info(f"Found {len(job_links)} job links in HTML")

        for link in job_links[:limit]:
            href = link.get('href')
            if not href:
                continue

            # Extract UUID from URL
            uuid_match = re.search(r'/stilling/([a-f0-9-]+)', href)
            if not uuid_match:
                continue

            uuid = uuid_match.group(1)

            # Build full URL
            if not href.startswith('http'):
                url = f"{self.BASE_URL}{href}"
            else:
                url = href

            # Try to extract title from link text or nearby elements
            title = link.get_text(strip=True)
            if not title:
                title = "Job Listing"

            jobs.append({
                'title': title,
                'company': 'Unknown',
                'location': 'Unknown',
                'url': url,
                'source': 'NAV',
                'keywords': keyword,
                'deadline': None,
                'job_type': None,
                'published': None,
                'description': None,
                'summary': None,
                'scraped_date': datetime.now(),
                'external_id': uuid,
                'status': 'ACTIVE',
            })

        return jobs

    async def scrape_all_keywords(
        self,
        keywords: List[str] = None,
        limit: int = None,
        last_etag: str = None,
        max_pages: int = 10
    ) -> tuple[List[Dict], Optional[str]]:
        """
        Scrape NAV jobs for all keywords using website search

        Args:
            keywords: List of keywords to search (default from settings)
            limit: Maximum total jobs to fetch (optional)
            last_etag: Not used for web scraping (kept for compatibility)
            max_pages: Not used for web scraping (kept for compatibility)

        Returns:
            Tuple of (list of jobs, None)
        """
        keywords = keywords or settings.get_keywords()
        all_jobs = []

        logger.info(f"Starting NAV web scraping with {len(keywords)} keywords")

        # Get location from settings
        location = settings.nav_municipal  # e.g., "VESTLAND.BERGEN"

        for keyword in keywords:
            try:
                jobs = await self.search_jobs(
                    keyword=keyword,
                    location=location,
                    limit=limit or 100
                )

                all_jobs.extend(jobs)

                # Check limit
                if limit and len(all_jobs) >= limit:
                    all_jobs = all_jobs[:limit]
                    break

                # Rate limiting
                if settings.request_delay > 0:
                    import asyncio
                    await asyncio.sleep(settings.request_delay)

            except Exception as e:
                logger.error(f"Error scraping keyword '{keyword}': {e}")
                continue

        logger.info(f"Scraped {len(all_jobs)} total jobs from NAV website")
        return all_jobs, None
