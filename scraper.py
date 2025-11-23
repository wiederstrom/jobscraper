"""
Combined job scraper for FINN.no and NAV.no
Saves results to PostgreSQL database
"""

import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional
import config

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use keywords from config
KEYWORDS = config.KEYWORDS

class JobScraper:
    def __init__(self):
        self.conn = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT
        })

    def setup_database(self):
        """Initialize PostgreSQL database with jobs table"""
        conn = config.get_database_connection()

        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS jobs
                   (id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    url TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL,
                    keywords TEXT,
                    deadline TEXT,
                    job_type TEXT,
                    published TEXT,
                    scraped_date TIMESTAMP NOT NULL,
                    description TEXT,
                    is_hidden BOOLEAN DEFAULT FALSE,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    applied BOOLEAN DEFAULT FALSE,
                    applied_date TIMESTAMP,
                    notes TEXT)''')
        conn.commit()

        return conn

    # ===== FINN.NO SCRAPER =====

    def scrape_finn_jobs(self) -> List[Dict]:
        """Scrape jobs from Finn.no"""
        logger.info("Fetching jobs from FINN.no")

        all_jobs = []
        seen_urls = set()

        # Determine which keywords to search
        keywords_to_search = KEYWORDS[:config.MAX_KEYWORDS] if config.MAX_KEYWORDS > 0 else KEYWORDS
        logger.info(f"Searching {len(keywords_to_search)} keywords")

        for keyword in keywords_to_search:
            try:
                jobs = self._scrape_finn_keyword(keyword)

                # Add only unique jobs
                for job in jobs:
                    if job['url'] not in seen_urls:
                        all_jobs.append(job)
                        seen_urls.add(job['url'])

                time.sleep(1)  # Be polite between searches

            except Exception as e:
                logger.warning(f"Failed to scrape FINN for keyword '{keyword}': {e}")
                continue

        logger.info(f"Found {len(all_jobs)} unique jobs from FINN.no")
        return all_jobs

    def _scrape_finn_keyword(self, keyword: str) -> List[Dict]:
        """Scrape FINN.no for a specific keyword"""
        # Add quotes for multi-word queries
        query = f'"{keyword}"' if ' ' in keyword else keyword

        url = f"https://www.finn.no/job/search?location={config.FINN_LOCATION}&q={query}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch FINN search for '{keyword}': {e}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find job links
        job_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/job/ad/' in href:
                if href.startswith('/'):
                    href = f"https://www.finn.no{href}"
                job_links.append(href)

        # Remove duplicates and limit per keyword
        job_links = list(set(job_links))[:config.MAX_JOBS_PER_KEYWORD]

        # Scrape each job
        jobs = []
        for job_url in job_links:
            try:
                job_data = self._parse_finn_job(job_url, keyword)
                if job_data:
                    jobs.append(job_data)
                time.sleep(0.5)  # Be polite
            except Exception as e:
                logger.debug(f"Failed to parse FINN job {job_url}: {e}")
                continue

        return jobs

    def _parse_finn_job(self, url: str, search_keyword: str) -> Optional[Dict]:
        """Parse a single FINN job page"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.debug(f"Failed to fetch FINN job page: {e}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title
        title_element = soup.select_one('h2.t2')
        if not title_element:
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
            if 'flex flex-col' in li.get('class', []):
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

        # Use the search keyword that found this job
        keywords_str = search_keyword

        return {
            'title': title,
            'company': company,
            'location': location,
            'url': url,
            'source': 'FINN',
            'keywords': keywords_str,
            'deadline': deadline,
            'job_type': job_type,
            'published': published,
            'description': description
        }

    # ===== NAV.NO SCRAPER =====

    def scrape_nav_jobs(self) -> List[Dict]:
        """Scrape jobs from NAV.no (Arbeidsplassen)"""
        logger.info("Fetching jobs from NAV.no")

        all_jobs = []
        seen_urls = set()

        # Determine which keywords to search
        keywords_to_search = KEYWORDS[:config.MAX_KEYWORDS] if config.MAX_KEYWORDS > 0 else KEYWORDS
        logger.info(f"Searching {len(keywords_to_search)} keywords")

        for keyword in keywords_to_search:
            try:
                jobs = self._scrape_nav_keyword(keyword)

                # Add only unique jobs
                for job in jobs:
                    if job['url'] not in seen_urls:
                        all_jobs.append(job)
                        seen_urls.add(job['url'])

                time.sleep(1)  # Be polite between searches

            except Exception as e:
                logger.warning(f"Failed to scrape NAV for keyword '{keyword}': {e}")
                continue

        logger.info(f"Found {len(all_jobs)} unique jobs from NAV.no")
        return all_jobs

    def _scrape_nav_keyword(self, keyword: str) -> List[Dict]:
        """Scrape NAV.no for a specific keyword"""
        # Add quotes for multi-word queries
        query = f'"{keyword}"' if ' ' in keyword else keyword

        # Build search URL using configured location
        url = f"https://arbeidsplassen.nav.no/stillinger?county={config.NAV_COUNTY}&v=5&municipal={config.NAV_MUNICIPAL}&q={query}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch NAV search for '{keyword}': {e}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find job links
        job_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/stillinger/stilling/' in href or '/stilling/' in href:
                if href.startswith('/'):
                    href = f"https://arbeidsplassen.nav.no{href}"
                job_links.append(href)

        # Remove duplicates and limit per keyword
        job_links = list(set(job_links))[:config.MAX_JOBS_PER_KEYWORD]

        # Scrape each job
        jobs = []
        for job_url in job_links:
            try:
                job_data = self._parse_nav_job(job_url, keyword)
                if job_data:
                    jobs.append(job_data)
                time.sleep(0.5)  # Be polite
            except Exception as e:
                logger.debug(f"Failed to parse NAV job {job_url}: {e}")
                continue

        return jobs

    def _parse_nav_job(self, url: str, search_keyword: str) -> Optional[Dict]:
        """Parse a single NAV job page"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.debug(f"Failed to fetch NAV job page: {e}")
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract title
        title_elem = soup.select_one('h1')
        if not title_elem:
            return None
        title = title_elem.get_text(strip=True)

        # Extract company and location
        company_elements = soup.find_all('p', class_='navds-body-long navds-body-long--medium navds-typo--semibold')
        company = company_elements[0].get_text(strip=True) if len(company_elements) >= 1 else "Unknown"
        location = company_elements[1].get_text(strip=True) if len(company_elements) >= 2 else "Unknown"

        # Extract deadline
        deadline = None
        for p_tag in soup.find_all('p', class_='navds-body-long navds-body-long--medium'):
            text = p_tag.get_text(strip=True)
            if 'Søk senest' in text or 'søk senest' in text:
                deadline = text.replace('Søk senest', '').replace('søk senest', '').strip()
                break

        # Extract job type
        job_type = None
        for dt_tag in soup.find_all('dt', class_='navds-label'):
            if 'Type ansettelse' in dt_tag.get_text():
                dd_tag = dt_tag.find_next_sibling('dd')
                if dd_tag:
                    job_type = dd_tag.get_text(strip=True)
                    break

        # Extract full job description
        description = None
        description_element = soup.select_one('div.arb-rich-text.job-posting-text')
        if description_element:
            description = description_element.get_text(separator='\n', strip=True)

        # Use the search keyword that found this job
        keywords_str = search_keyword

        return {
            'title': title,
            'company': company,
            'location': location,
            'url': url,
            'source': 'NAV',
            'keywords': keywords_str,
            'deadline': deadline,
            'job_type': job_type,
            'description': description
        }

    # ===== DATABASE METHODS =====

    def save_new_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Save new jobs to database (preserves user interaction data)"""
        if not self.conn:
            self.conn = self.setup_database()

        new_jobs = []
        cursor = self.conn.cursor()

        for job in jobs:
            try:
                cursor.execute(
                    '''INSERT INTO jobs (title, company, location, url, source, keywords, deadline, job_type, published, scraped_date, description)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (job['title'], job['company'], job.get('location'), job['url'],
                     job['source'], job['keywords'], job.get('deadline'), job.get('job_type'),
                     job.get('published'), datetime.now(), job.get('description'))
                )
                new_jobs.append(job)
                logger.debug(f"Saved new job: {job['title']} from {job['source']}")
            except Exception:
                # Job already exists (IntegrityError on duplicate URL)
                logger.debug(f"Job already exists: {job['title']}")
                pass

        self.conn.commit()
        return new_jobs

    def get_all_jobs(self) -> List[Dict]:
        """Retrieve all jobs from database"""
        if not self.conn:
            self.conn = self.setup_database()

        cursor = self.conn.cursor()
        cursor.execute(
            '''SELECT title, company, location, url, source, keywords, deadline, job_type, published,
                      scraped_date, description, is_hidden, is_favorite, applied, applied_date, notes
               FROM jobs ORDER BY scraped_date DESC'''
        )

        # PostgreSQL with RealDictCursor returns dictionaries
        jobs = [dict(row) for row in cursor.fetchall()]
        return jobs

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

def main():
    scraper = JobScraper()

    try:
        logger.info("Starting job scraper...")

        # Scrape from both sources
        all_jobs = []

        # FINN.no
        logger.info("\n" + "="*60)
        logger.info("Scraping FINN.no")
        logger.info("="*60)
        finn_jobs = scraper.scrape_finn_jobs()
        all_jobs.extend(finn_jobs)
        logger.info(f"Found {len(finn_jobs)} jobs from FINN.no")

        # NAV.no
        logger.info("\n" + "="*60)
        logger.info("Scraping NAV.no")
        logger.info("="*60)
        nav_jobs = scraper.scrape_nav_jobs()
        all_jobs.extend(nav_jobs)
        logger.info(f"Found {len(nav_jobs)} jobs from NAV.no")

        if not all_jobs:
            logger.warning("No jobs found matching the criteria")
            return

        # Save new jobs
        new_jobs = scraper.save_new_jobs(all_jobs)

        # Display results
        print("\n" + "="*60)
        print(f"RESULTS: Found {len(new_jobs)} new jobs")
        print("="*60 + "\n")

        if new_jobs:
            for job in new_jobs:
                print(f" {job['title']}")
                print(f"   Company: {job['company']}")
                print(f"   Location: {job.get('location', 'Unknown')}")
                print(f"   Source: {job['source']}")
                print(f"   Keywords: {job['keywords']}")
                if job.get('deadline'):
                    print(f"   Deadline: {job['deadline']}")
                if job.get('job_type'):
                    print(f"   Type: {job['job_type']}")
                if job.get('published'):
                    print(f"   Published: {job['published']}")
                print(f"   URL: {job['url']}\n")
        else:
            print("ℹ️  No new jobs found (all jobs already in database)\n")

        # Show statistics
        all_saved_jobs = scraper.get_all_jobs()
        print("="*60)
        print(f"Total jobs in database: {len(all_saved_jobs)}")

        # Stats by source
        finn_count = sum(1 for j in all_saved_jobs if j['source'] == 'FINN')
        nav_count = sum(1 for j in all_saved_jobs if j['source'] == 'NAV')
        print(f"   - FINN: {finn_count}")
        print(f"   - NAV: {nav_count}")
        print("="*60)

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
