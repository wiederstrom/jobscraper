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

                # Try to find embedded JSON data in various formats
                ads = []

                # Method 1: Look for __NEXT_DATA__ script
                scripts = soup.find_all('script', id='__NEXT_DATA__')
                if scripts:
                    try:
                        page_data = json.loads(scripts[0].string)
                        props = page_data.get('props', {}).get('pageProps', {})
                        search_result = props.get('searchResult', {})
                        ads = search_result.get('ads', [])
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.debug(f"__NEXT_DATA__ parsing failed: {e}")

                # Method 2: Look for JSON in other script tags
                if not ads:
                    all_scripts = soup.find_all('script', type='application/json')
                    for script in all_scripts:
                        try:
                            script_data = json.loads(script.string)
                            # Look for ads array in various locations
                            if isinstance(script_data, dict):
                                if 'ads' in script_data:
                                    ads = script_data['ads']
                                    break
                                elif 'searchResult' in script_data:
                                    ads = script_data.get('searchResult', {}).get('ads', [])
                                    break
                        except:
                            continue

                if ads:
                    logger.info(f"Found {len(ads)} jobs from embedded JSON for keyword '{keyword}'")
                    for ad in ads[:limit]:
                        job = self._parse_job_from_data(ad, keyword)
                        if job:
                            jobs.append(job)
                else:
                    # Fallback: Parse HTML and fetch individual job pages
                    logger.info(f"No embedded JSON found, falling back to HTML parsing")
                    jobs = await self._parse_jobs_from_html_and_fetch(soup, keyword, limit)

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

    async def _parse_jobs_from_html_and_fetch(self, soup: BeautifulSoup, keyword: str, limit: int) -> List[Dict]:
        """
        Fallback: Parse job URLs from HTML and fetch individual pages

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

        logger.info(f"Found {len(job_links)} job links in HTML, fetching details...")

        seen_uuids = set()

        for link in job_links[:limit * 2]:  # Get more links since there might be duplicates
            if len(jobs) >= limit:
                break

            href = link.get('href')
            if not href:
                continue

            # Extract UUID from URL
            uuid_match = re.search(r'/stilling/([a-f0-9-]+)', href)
            if not uuid_match:
                continue

            uuid = uuid_match.group(1)

            # Skip duplicates
            if uuid in seen_uuids:
                continue
            seen_uuids.add(uuid)

            # Build full URL
            if not href.startswith('http'):
                url = f"{self.BASE_URL}{href}"
            else:
                url = href

            # Fetch the individual job page to get full details
            job = await self._fetch_job_page(url, uuid, keyword)
            if job:
                jobs.append(job)

            # Rate limiting
            if settings.request_delay > 0:
                import asyncio
                await asyncio.sleep(settings.request_delay)

        logger.info(f"Fetched details for {len(jobs)} jobs")
        return jobs

    async def _fetch_job_page(self, url: str, uuid: str, keyword: str) -> Optional[Dict]:
        """
        Fetch and parse an individual job using NAV public API

        Args:
            url: Job page URL
            uuid: Job UUID
            keyword: Search keyword

        Returns:
            Parsed job dictionary or None
        """
        try:
            # Use NAV public API to fetch job details
            api_url = f"https://arbeidsplassen.nav.no/public-api/ad/{uuid}"

            async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
                response = await client.get(api_url, headers={'Accept': 'application/json'})
                response.raise_for_status()

                job_data = response.json()

                # Extract data from the API response
                title = job_data.get('title', 'Job Listing')

                # Get employer/company
                employer = job_data.get('employer', {})
                company = employer.get('name', 'Unknown')

                # Get location
                location_list = job_data.get('locationList', [])
                location = location_list[0] if location_list else 'Bergen'

                # Get dates
                published = job_data.get('published')
                expires = job_data.get('expires')
                application_due = job_data.get('applicationDue')

                # Get description and other details
                description = job_data.get('description')
                properties = job_data.get('properties', {})
                job_type = properties.get('extent')

                return {
                    'title': title,
                    'company': company,
                    'location': location,
                    'url': url,
                    'source': 'NAV',
                    'keywords': keyword,
                    'deadline': application_due or expires,
                    'job_type': job_type,
                    'published': published,
                    'description': description,
                    'summary': None,
                    'scraped_date': datetime.now(),
                    'external_id': uuid,
                    'status': 'ACTIVE',
                }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching job {uuid} from API: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching job {uuid}: {e}")
            return None

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
