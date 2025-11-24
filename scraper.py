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
from anthropic import Anthropic
from urllib.parse import quote

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

        # Initialize Claude client if summarization is enabled
        self.anthropic_client = None
        if (config.ENABLE_SUMMARIZATION or config.ENABLE_AI_FILTER) and config.ANTHROPIC_API_KEY:
            self.anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            logger.info(f"AI features enabled with Claude model: {config.AI_MODEL}")

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
                    summary TEXT,
                    is_hidden BOOLEAN DEFAULT FALSE,
                    is_favorite BOOLEAN DEFAULT FALSE,
                    applied BOOLEAN DEFAULT FALSE,
                    applied_date TIMESTAMP,
                    notes TEXT)''')
        conn.commit()

        return conn

    def summarize_description(self, description: str, title: str) -> Optional[str]:
        """Generate a concise summary of job description using Claude"""
        if not self.anthropic_client or not description or not config.ENABLE_SUMMARIZATION:
            return None

        try:
            # Use template and max chars from config
            prompt = config.SUMMARY_PROMPT_TEMPLATE.format(
                title=title,
                description=description[:config.MAX_SUMMARY_CHARS]
            )

            message = self.anthropic_client.messages.create(
                model=config.AI_MODEL,
                max_tokens=config.MAX_SUMMARY_TOKENS,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            summary = message.content[0].text.strip()
            logger.debug(f"Generated summary for: {title}")
            return summary

        except Exception as e:
            logger.warning(f"Failed to summarize job '{title}': {e}")
            return None

    def is_job_relevant(self, job: Dict) -> tuple[bool, str]:
        """
        Use Claude to determine if a job is relevant for spesific roles.
        Returns (is_relevant, reason)
        """
        if not self.anthropic_client or not config.ENABLE_AI_FILTER:
            return True, "AI filtering disabled"

        if not job.get('description') or not job.get('title'):
            return True, "Missing description or title"

        try:
            # Use template and max chars from config
            prompt = config.AI_FILTER_PROMPT_TEMPLATE.format(
                title=job['title'],
                keywords=job['keywords'],
                company=job.get('company', 'Ukjent'),
                description=job['description'][:config.MAX_FILTER_CHARS]
            )

            message = self.anthropic_client.messages.create(
                model=config.AI_MODEL,
                max_tokens=100,
                temperature=0.1,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response = message.content[0].text.strip()

            # Parse response
            is_relevant = response.upper().startswith("JA")
            reason = response[2:].strip() if len(response) > 2 else "No reason given"

            if is_relevant:
                logger.debug(f"Job RELEVANT: {job['title']} - {reason}")
            else:
                logger.info(f"Job FILTERED: {job['title']} - {reason}")

            return is_relevant, reason

        except Exception as e:
            logger.warning(f"Failed to filter job '{job['title']}': {e}")
            return True, f"Filter error: {e}"


    # ================================================== Felles Scrape Runner ==================================================

    def _run_keyword_scraper(self, keyword_scraper_method: callable, source_name: str) -> List[Dict]:
        """
        Handles the generic keyword loop, uniqueness check, and rate limiting.
        It takes a source-specific keyword scraping method as input.
        """
        logger.info(f"Fetching jobs from {source_name}")

        all_jobs = []
        seen_urls = set()

        # Determine which keywords to search based on config
        keywords_to_search = KEYWORDS[:config.MAX_KEYWORDS] if config.MAX_KEYWORDS > 0 else KEYWORDS
        logger.info(f"Searching {len(keywords_to_search)} keywords")

        for keyword in keywords_to_search:
            try:
                # Call the source-specific method (e.g., self._scrape_finn_keyword)
                jobs = keyword_scraper_method(keyword)

                # Add only unique jobs
                for job in jobs:
                    if job['url'] not in seen_urls:
                        all_jobs.append(job)
                        seen_urls.add(job['url'])

                time.sleep(1)  # Be polite between keyword searches 

            except Exception as e:
                logger.warning(f"Failed to scrape {source_name} for keyword '{keyword}': {e}")
                continue

        logger.info(f"Found {len(all_jobs)} unique jobs from {source_name}")
        return all_jobs

    def scrape_finn_jobs(self) -> List[Dict]:
        """Scrape jobs from Finn.no using the generic keyword runner."""
        return self._run_keyword_scraper(self._scrape_finn_keyword, "FINN.no")


    def _scrape_finn_keyword(self, keyword: str) -> List[Dict]:
        """Scrape FINN.no for a specific keyword"""
        # Add quotes for multi-word queries
        query = f'"{keyword}"' if ' ' in keyword else keyword

        url = f"https://www.finn.no/job/search?location={config.FINN_LOCATION}&q={query}" [cite: 1]

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch FINN search for '{keyword}': {e}")
            return []

        soup = BeautifulSoup(response.content, 'lxml')

        # Find job links
        job_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/job/ad/' in href:
                if href.startswith('/'):
                    href = f"https://www.finn.no{href}"
                job_links.append(href)

        # Remove duplicates and limit per keyword
        job_links = list(set(job_links))[:config.MAX_JOBS_PER_KEYWORD] [cite: 1]

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

        soup = BeautifulSoup(response.content, 'lxml')

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
            'description': description,
            'summary': None
        }

    # ================================================== NAV.NO SCRAPER ==================================================

    def scrape_nav_jobs(self) -> List[Dict]:
        """Scrape jobs from NAV.no (Arbeidsplassen) using the generic keyword runner."""
        return self._run_keyword_scraper(self._scrape_nav_keyword, "NAV.no")

    def _scrape_nav_keyword(self, keyword: str) -> List[Dict]:
        """Scrape NAV.no for a specific keyword"""
        # NAV.no doesn't support quoted queries well, use URL encoding instead
        query = quote(keyword)

        # Build search URL using configured location
        url = f"https://arbeidsplassen.nav.no/stillinger?county={config.NAV_COUNTY}&v=5&municipal={config.NAV_MUNICIPAL}&q={query}" [cite: 1]

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch NAV search for '{keyword}': {e}")
            return []

        soup = BeautifulSoup(response.content, 'lxml')

        # Find job links
        job_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/stillinger/stilling/' in href or '/stilling/' in href:
                if href.startswith('/'):
                    href = f"https://arbeidsplassen.nav.no{href}"
                job_links.append(href)

        # Remove duplicates and limit per keyword
        job_links = list(set(job_links))[:config.MAX_JOBS_PER_KEYWORD] [cite: 1]

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
        """Parse a single NAV job page (Now uses robust metadata extraction)"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.debug(f"Failed to fetch NAV job page: {e}")
            return None

        soup = BeautifulSoup(response.content, 'lxml')

        # Extract title
        title_elem = soup.select_one('h1')
        if not title_elem:
            return None
        title = title_elem.get_text(strip=True)

        company = "Unknown"
        location = "Unknown"

        # Robust extraction of Company and Location using SVG titles (Arbeidsgiver, Sted)
        metadata_stacks = soup.find_all('div', class_='navds-stack mb-2 navds-hstack navds-stack-gap')

        for stack in metadata_stacks:
            svg_title = stack.select_one('svg title')
            if svg_title:
                info_type = svg_title.get_text(strip=True)
                text_element = stack.select_one('p.navds-body-long--medium.navds-typo--semibold')
                
                if text_element:
                    value = text_element.get_text(strip=True)
                    
                    if info_type == 'Arbeidsgiver':
                        company = value
                    elif info_type == 'Sted':
                        location = value

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
            'description': description,
            'summary': None
        }

    # ================================================== DATABASE METHODS ==================================================

    def save_new_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """
        Save new jobs to database:
        1. Check for duplicates
        2. Filter relevancy 
        3. Generate summaries
        4. Save to database
        """
        if not self.conn:
            self.conn = self.setup_database()

        new_jobs = []
        filtered_count = 0
        cursor = self.conn.cursor()

        for job in jobs:
            # Step 1: duplicate check
            cursor.execute('SELECT id FROM jobs WHERE url = %s', (job['url'],))
            if cursor.fetchone():
                logger.debug(f"Job already exists: {job['title']}")
                continue

            # Step 2: Filter relevancy
            is_relevant, reason = self.is_job_relevant(job)
            if not is_relevant:
                filtered_count += 1
                continue

            # Step 3: Generate summary
            if config.ENABLE_SUMMARIZATION and job.get('description'):
                job['summary'] = self.summarize_description(job['description'], job['title'])
            else:
                job['summary'] = None

            # Step 4: Save to database
            try:
                # Ensure 'summary' is included in the INSERT statement
                cursor.execute(
                    '''INSERT INTO jobs (title, company, location, url, source, keywords, deadline, job_type, published, scraped_date, description, summary)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                    (job['title'], job['company'], job.get('location'), job['url'],
                     job['source'], job['keywords'], job.get('deadline'), job.get('job_type'),
                     job.get('published'), datetime.now(), job.get('description'), job.get('summary'))
                )
                new_jobs.append(job)
                logger.info(f"Saved new job: {job['title']} from {job['source']}")
            except Exception as e:
                logger.error(f"Failed to save job '{job['title']}': {e}")

        self.conn.commit()

        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} irrelevant jobs")

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
        logger.info("\n" + "_"*40)
        finn_jobs = scraper.scrape_finn_jobs()
        all_jobs.extend(finn_jobs)
        logger.info(f"Finished scraping FINN.no")

        # NAV.no
        logger.info("\n" + "_"*40)
        nav_jobs = scraper.scrape_nav_jobs()
        all_jobs.extend(nav_jobs)
        logger.info(f"Finished scraping NAV.no")

        if not all_jobs:
            logger.warning("No jobs found matching the criteria")
            return

        # Save new jobs
        new_jobs = scraper.save_new_jobs(all_jobs)

        # Display results
        print("\n" + "_"*40)
        print(f"RESULTS: Found {len(new_jobs)} new jobs")
        print("_"*40 + "\n")

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
            print("No new jobs found (all jobs already in database)\n")

        # Show statistics
        all_saved_jobs = scraper.get_all_jobs()
        print("_"*40)
        print(f"Total jobs in database: {len(all_saved_jobs)}")

        # Stats by source
        finn_count = sum(1 for j in all_saved_jobs if j['source'] == 'FINN')
        nav_count = sum(1 for j in all_saved_jobs if j['source'] == 'NAV')
        print(f"   - from FINN.no: {finn_count}")
        print(f"   - from NAV.no: {nav_count}")
        print("_"*40)

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
