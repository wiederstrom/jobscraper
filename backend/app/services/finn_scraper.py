"""
FINN.no Job Scraper Service
Scrapes tech job listings from FINN.no
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime
import logging
from urllib.parse import urlencode

from app.config import settings

logger = logging.getLogger(__name__)


class FINNScraper:
    """Scraper for FINN.no job listings"""

    BASE_URL = "https://www.finn.no/job/search"

    def __init__(self):
        self.headers = {
            'User-Agent': settings.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    async def search_jobs(self, keyword: str, location: str = None, limit: int = 100) -> List[Dict]:
        """
        Search for jobs on FINN.no by keyword (two-step process)

        Step 1: Get job URLs from search page
        Step 2: Scrape each job detail page

        Args:
            keyword: Search keyword
            location: FINN location code (default from settings)
            limit: Maximum number of jobs to fetch

        Returns:
            List of job dictionaries
        """
        location = location or settings.finn_location
        jobs = []

        # Add quotes for multi-word queries (like original scraper)
        query = f'"{keyword}"' if ' ' in keyword else keyword

        params = {
            'q': query,
            'location': location
        }

        url = f"{self.BASE_URL}?{urlencode(params)}"
        logger.info(f"Scraping FINN.no for keyword: {keyword}")

        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
                # Step 1: Get search results page to find job URLs
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'lxml')

                # Find all links containing '/job/ad/' (individual job postings)
                job_urls = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/job/ad/' in href:
                        if href.startswith('/'):
                            href = f"https://www.finn.no{href}"
                        job_urls.append(href)

                # Remove duplicates and limit
                job_urls = list(set(job_urls))[:limit]

                logger.info(f"Found {len(job_urls)} job URLs for keyword '{keyword}'")

                # Step 2: Fetch each job detail page
                for job_url in job_urls:
                    try:
                        job_data = await self._fetch_and_parse_job(client, job_url, keyword)
                        if job_data:
                            jobs.append(job_data)

                        # Rate limiting between individual job fetches
                        if settings.request_delay > 0:
                            import asyncio
                            await asyncio.sleep(settings.request_delay)

                    except Exception as e:
                        logger.debug(f"Failed to parse FINN job {job_url}: {e}")
                        continue

                logger.info(f"Successfully scraped {len(jobs)} jobs for keyword '{keyword}'")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error scraping FINN.no: {e}")
        except Exception as e:
            logger.error(f"Error scraping FINN.no: {e}")

        return jobs

    async def _fetch_and_parse_job(self, client: httpx.AsyncClient, url: str, search_keyword: str) -> Optional[Dict]:
        """
        Fetch and parse a single FINN job page

        Args:
            client: HTTP client to use for request
            url: FINN.no job posting URL
            search_keyword: The keyword that found this job

        Returns:
            Dictionary with job data or None if parsing fails
        """
        try:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'lxml')

            # Extract title
            title_element = soup.select_one('h2.t2')
            if not title_element:
                logger.debug(f"No title found for {url}")
                return None
            title = title_element.get_text(strip=True)

            # Extract company
            company_element = soup.select_one('section.mt-16 p.mb-24')
            company = company_element.get_text(strip=True) if company_element else "Unknown"

            # Extract location
            location_element = soup.select_one('a[href*="location="]')
            location = location_element.get_text(strip=True) if location_element else "Unknown"

            # Extract job type
            job_type = None
            for li in soup.find_all('li'):
                if 'flex' in li.get('class', []) and 'flex-col' in li.get('class', []):
                    text = li.get_text(strip=True)
                    if 'Ansettelsesform' in text:
                        span = li.find('span', class_='font-bold')
                        if span:
                            job_type = span.get_text(strip=True)
                            break

            # Extract deadline
            deadline = None
            for li in soup.find_all('li'):
                if 'flex' in li.get('class', []) and 'flex-col' in li.get('class', []):
                    text = li.get_text(strip=True)
                    if 'Frist' in text:
                        span = li.find('span', class_='font-bold')
                        if span:
                            deadline = span.get_text(strip=True)
                            break

            # Extract published date
            published = None
            for li in soup.find_all('li'):
                classes = li.get('class', [])
                if 'flex' in classes and 'gap-x-16' in classes:
                    text = li.get_text(strip=True)
                    if 'Sist endret' in text:
                        time_tag = li.find('time')
                        if time_tag:
                            published = time_tag.get_text(strip=True)
                            break

            # Extract full job description
            description = None
            description_element = soup.select_one('div.import-decoration')
            if description_element:
                description = description_element.get_text(separator='\n', strip=True)

            return {
                'title': title,
                'company': company,
                'location': location,
                'url': url,
                'source': 'FINN',
                'keywords': search_keyword,
                'deadline': deadline,
                'job_type': job_type,
                'published': published,
                'description': description,
                'summary': None,  # Will be generated by AI service
                'scraped_date': datetime.now(),
                'status': 'ACTIVE',
            }

        except httpx.HTTPError as e:
            logger.debug(f"HTTP error fetching FINN job {url}: {e}")
            return None
        except Exception as e:
            logger.debug(f"Error parsing FINN job {url}: {e}")
            return None

    async def scrape_all_keywords(self, keywords: List[str] = None, limit_per_keyword: int = None) -> List[Dict]:
        """
        Scrape jobs for all keywords

        Args:
            keywords: List of keywords to search (default from settings)
            limit_per_keyword: Max jobs per keyword (default from settings)

        Returns:
            List of all job dictionaries
        """
        keywords = keywords or settings.get_keywords()
        limit_per_keyword = limit_per_keyword or settings.max_jobs_per_keyword

        # Apply max keywords limit if set
        if settings.max_keywords > 0:
            keywords = keywords[:settings.max_keywords]

        all_jobs = []

        for keyword in keywords:
            jobs = await self.search_jobs(keyword, limit=limit_per_keyword)
            all_jobs.extend(jobs)

            # Rate limiting - delay between requests
            if settings.request_delay > 0:
                import asyncio
                await asyncio.sleep(settings.request_delay)

        # Deduplicate by URL
        seen_urls = set()
        unique_jobs = []
        for job in all_jobs:
            if job['url'] not in seen_urls:
                seen_urls.add(job['url'])
                unique_jobs.append(job)

        logger.info(f"Scraped {len(unique_jobs)} unique jobs from {len(keywords)} keywords")
        return unique_jobs
