"""
Configuration management for job scraper
Uses PostgreSQL database
"""

import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

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
    KEYWORDS = [kw.strip() for kw in KEYWORDS_ENV.split(',')]
else:
    KEYWORDS = [
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

def get_database_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
