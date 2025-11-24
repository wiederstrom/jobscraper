"""
Configuration management for job scraper
Uses PostgreSQL database
"""

import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List

# Load environment variables from .env file
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Scraper configuration
FINN_LOCATION = os.getenv('FINN_LOCATION', '2.20001.22046.20220')  # Bergen location code
NAV_COUNTY = os.getenv('NAV_COUNTY', 'VESTLAND')  # County for NAV search
NAV_MUNICIPAL = os.getenv('NAV_MUNICIPAL', 'VESTLAND.BERGEN')  # Municipality for NAV search
MAX_JOBS_PER_KEYWORD = int(os.getenv('MAX_JOBS_PER_KEYWORD', '5'))  # Limit results per keyword to avoid duplicates
MAX_KEYWORDS = int(os.getenv('MAX_KEYWORDS', '0'))  # Limit number of keywords to search (0 = all)

# Keywords for job search (can be overridden via environment variable)
KEYWORDS_ENV = os.getenv('KEYWORDS')
if KEYWORDS_ENV:
    KEYWORDS: List[str] = [kw.strip() for kw in KEYWORDS_ENV.split(',')]
else:
    KEYWORDS: List[str] = [
        # Programming languages
        'python', 'r programming', 'sql', 'scala', 'java',

        # Data science & ML
        'machine learning', 'deep learning', 'data scientist', 'data science',
        'data analyst', 'data engineer', 'ml engineer', 'mlops',
        'statistiker', 'statistics', 'statistical analysis',

        # Libraries & frameworks
        'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch',
        'keras', 'spark', 'pyspark', 'airflow', 'dbt',

        # Cloud & infrastructure
        'azure', 'aws', 'gcp', 'google cloud', 'docker', 'kubernetes',

        # BI & visualization
        'tableau', 'power bi', 'data visualization',

        # Specializations
        'natural language processing', 'computer vision',
        'big data', 'data engineering', 'analytics', 'business intelligence'
    ]

# Request settings
REQUEST_TIMEOUT = 10  # seconds
REQUEST_DELAY = 1  # seconds between requests to be polite

# User agent for requests
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Logging settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Claude Summarization and Filtering settings
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
ENABLE_SUMMARIZATION = os.getenv('ENABLE_SUMMARIZATION', 'false').lower() == 'true'
ENABLE_AI_FILTER = os.getenv('ENABLE_AI_FILTER', 'false').lower() == 'true'

# Claude Model parameters
AI_MODEL = os.getenv('AI_MODEL', 'claude-3-haiku-20240307')
MAX_SUMMARY_TOKENS = 300
MAX_SUMMARY_CHARS = 3000  # Max chars to send to model for summarization
MAX_FILTER_CHARS = 1500  # Max chars to send to model for filtering

# Claude Prompt Templates
SUMMARY_PROMPT_TEMPLATE = """Oppsummer denne jobbeskrivelsen kort på norsk (maks 4-5 setninger).

Stillingstittel: {title}

Fokuser på:
- Hovedansvar og arbeidsoppgaver
- Viktigste kvalifikasjoner/kompetanse
- Relevante teknologier eller verktøy

Jobbeskrivelse:
{description}

Gi en kort, konsis oppsummering:"""

AI_FILTER_PROMPT_TEMPLATE = """Vurder om denne jobben er relevant for en person som søker data/tech/analytics-stillinger.

Stillingstittel: {title}
Søkeord som fant jobben: {keywords}
Bedrift: {company}

Jobbeskrivelse (utdrag):
{description}

Svar med BARE "JA" eller "NEI" etterfulgt av en kort forklaring (1 setning).

Kriterier for JA:
- Stillingen er innen data/IT/tech/analytics (data analyst, data engineer, data scientist, business intelligence, backend/frontend developer, etc.)
- Søkeordet er en HOVEDKOMPETANSE for stillingen, ikke bare nevnt i forbifarten
- For fler-ord søkeord (f.eks "data engineer"): ordene må opptre sammen som en faktisk stillingstittel eller rolle, ikke separat

Kriterier for NEI:
- Stillingen er i et annet felt (økonomi, psykologi, elektriker, etc.) selv om de nevner verktøy som Power BI eller Excel
- Søkeordet er bare nevnt som et verktøy/nice-to-have, men er ikke kjernen i jobben
- For "data engineer": jobben er "electrical engineer" eller annet ingeniørfelt som tilfeldigvis nevner data
- For "power bi": jobben er controller/økonom som bare bruker Power BI til rapportering
- Jobben er et stipendiat, eller en jobb innen forskning
Svar:"""


def get_database_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)