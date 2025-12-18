"""
AI Service for Job Filtering and Summarization
Uses Anthropic Claude for relevancy filtering and Norwegian summaries
"""

from anthropic import Anthropic
from typing import Optional
import logging

from app.config import settings, AI_FILTER_PROMPT_TEMPLATE, SUMMARY_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered job filtering and summarization"""

    def __init__(self):
        self.client = None
        if settings.anthropic_api_key:
            self.client = Anthropic(api_key=settings.anthropic_api_key)
        else:
            logger.warning("ANTHROPIC_API_KEY not set - AI features disabled")

    def is_enabled(self) -> bool:
        """Check if AI service is available"""
        return self.client is not None

    async def filter_job(
        self,
        title: str,
        company: str,
        description: str,
        keywords: str
    ) -> tuple[bool, Optional[str]]:
        """
        Use AI to determine if a job is relevant for data/tech/analytics positions

        Args:
            title: Job title
            company: Company name
            description: Job description
            keywords: Keywords that found this job

        Returns:
            Tuple of (is_relevant, explanation)
        """
        if not self.client or not settings.enable_ai_filter:
            # Default to accepting all jobs if AI filter is disabled
            return True, "AI filtering disabled"

        try:
            # Truncate description to max length
            truncated_desc = description[:settings.max_filter_chars] if description else ""

            # Format prompt
            prompt = AI_FILTER_PROMPT_TEMPLATE.format(
                title=title,
                keywords=keywords,
                company=company,
                description=truncated_desc
            )

            # Call Claude
            message = self.client.messages.create(
                model=settings.ai_model,
                max_tokens=100,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text.strip()

            # Parse response - should start with "JA" or "NEI"
            is_relevant = response_text.upper().startswith("JA")
            explanation = response_text

            logger.info(f"AI Filter: {title[:50]}... -> {'RELEVANT' if is_relevant else 'IRRELEVANT'}")

            return is_relevant, explanation

        except Exception as e:
            logger.error(f"Error in AI filtering: {e}")
            # Default to accepting on error
            return True, f"Error: {str(e)}"

    async def generate_summary(
        self,
        title: str,
        description: str
    ) -> Optional[str]:
        """
        Generate a Norwegian summary of the job description using AI

        Args:
            title: Job title
            description: Job description

        Returns:
            Norwegian summary or None if summarization fails
        """
        if not self.client or not settings.enable_summarization:
            return None

        try:
            # Truncate description to max length
            truncated_desc = description[:settings.max_summary_chars] if description else ""

            if not truncated_desc:
                return None

            # Format prompt
            prompt = SUMMARY_PROMPT_TEMPLATE.format(
                title=title,
                description=truncated_desc
            )

            # Call Claude
            message = self.client.messages.create(
                model=settings.ai_model,
                max_tokens=settings.max_summary_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            summary = message.content[0].text.strip()

            logger.info(f"Generated summary for: {title[:50]}...")

            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None
