"""
Configuration management for job scraper API
Uses Pydantic Settings for type-safe configuration with validation
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Database
    database_url: str = Field(..., alias="DATABASE_URL", description="PostgreSQL connection string")

    # Location settings
    finn_location: str = Field(
        default="2.20001.22046.20220",
        alias="FINN_LOCATION",
        description="FINN.no location code (Bergen)"
    )
    nav_county: str = Field(
        default="VESTLAND",
        alias="NAV_COUNTY",
        description="NAV county filter"
    )
    nav_municipal: str = Field(
        default="VESTLAND.BERGEN",
        alias="NAV_MUNICIPAL",
        description="NAV municipality filter"
    )

    # NAV API
    nav_api_token: Optional[str] = Field(
        default=None,
        alias="NAV_API_TOKEN",
        description="NAV API JWT bearer token"
    )

    # Scraper limits
    max_jobs_per_keyword: int = Field(
        default=100,
        alias="MAX_JOBS_PER_KEYWORD",
        description="Maximum jobs to fetch per keyword"
    )
    max_keywords: int = Field(
        default=0,
        alias="MAX_KEYWORDS",
        description="Maximum keywords to search (0 = all)"
    )

    # Request settings
    request_timeout: int = Field(
        default=10,
        description="HTTP request timeout in seconds"
    )
    request_delay: int = Field(
        default=1,
        description="Delay between requests in seconds"
    )

    # User agent
    user_agent: str = Field(
        default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="HTTP User-Agent header"
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    # AI Configuration
    anthropic_api_key: Optional[str] = Field(
        default=None,
        alias="ANTHROPIC_API_KEY",
        description="Anthropic Claude API key"
    )
    enable_summarization: bool = Field(
        default=False,
        alias="ENABLE_SUMMARIZATION",
        description="Enable AI job description summarization"
    )
    enable_ai_filter: bool = Field(
        default=False,
        alias="ENABLE_AI_FILTER",
        description="Enable AI relevancy filtering"
    )
    ai_model: str = Field(
        default="claude-3-haiku-20240307",
        alias="AI_MODEL",
        description="Claude model to use"
    )
    max_summary_tokens: int = Field(
        default=300,
        description="Maximum tokens for summary generation"
    )
    max_summary_chars: int = Field(
        default=3000,
        description="Maximum characters to send for summarization"
    )
    max_filter_chars: int = Field(
        default=1500,
        description="Maximum characters to send for filtering"
    )

    # Keywords (can be overridden via environment)
    keywords: Optional[str] = Field(
        default=None,
        alias="KEYWORDS",
        description="Comma-separated list of keywords (overrides default)"
    )

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins for React frontend"
    )

    # API settings
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="API version 1 prefix"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        populate_by_name=True
    )

    @field_validator("enable_summarization", "enable_ai_filter", mode="before")
    @classmethod
    def parse_bool(cls, v):
        """Parse boolean from string"""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)

    def get_keywords(self) -> List[str]:
        """Get keywords list - either from env override or default list"""
        if self.keywords:
            return [kw.strip() for kw in self.keywords.split(',')]
        return DEFAULT_KEYWORDS


# Default keywords list (preserved from old config.py)
DEFAULT_KEYWORDS: List[str] = [
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

# AI Prompt Templates (CRITICAL: Preserved exactly from old config.py)
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


# Global settings instance
settings = Settings()
