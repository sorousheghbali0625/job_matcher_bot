import re
import logging
from typing import List

from models.schemas import JobPost, UserPreferences

logger = logging.getLogger(__name__)

class RuleBasedFilter:
    """
    Handles fast, deterministic filtering of job posts before they reach 
    the more expensive Vector DB or LLM evaluation stages.
    """

    @staticmethod
    def _passes_budget(job_budget: float | None, user_min_budget: float) -> bool:
        """
        Checks if the job meets the user's minimum budget requirements.
        """
        # If the scraper couldn't find a budget (None), we let it pass. 
        # We don't want to prematurely filter out negotiable opportunities.
        if job_budget is None:
            return True
        return job_budget >= user_min_budget

    @staticmethod
    def _has_unwanted_keywords(job_title: str, job_description: str, unwanted_keywords: List[str]) -> bool:
        """
        Checks if any of the user's unwanted keywords appear in the job post.
        Uses word boundaries to prevent partial word matches.
        """
        if not unwanted_keywords:
            return False

        # Combine title and description and lowercase for case-insensitive matching
        full_text = f"{job_title} {job_description}".lower()

        for keyword in unwanted_keywords:
            # \b ensures we match exact words. 
            # e.g., Unwanted keyword "C" won't match the "c" in "React"
            pattern = rf"\b{re.escape(keyword.lower())}\b"
            if re.search(pattern, full_text):
                return True
        
        return False

    @classmethod
    async def evaluate(cls, job: JobPost, user: UserPreferences) -> bool:
        """
        Evaluates a job post against a single tenant's rigid rules.
        
        Args:
            job: The incoming JobPost data contract.
            user: The specific UserPreferences to check against.
            
        Returns:
            bool: True if the job passes all rules, False if it is rejected.
        """
        try:
            # 1. Budget check
            if not cls._passes_budget(job.budget, user.min_budget):
                logger.debug(f"Job {job.job_id} rejected for User {user.user_id}: Budget too low.")
                return False

            # 2. Unwanted keywords check
            if cls._has_unwanted_keywords(job.title, job.description, user.unwanted_keywords):
                logger.debug(f"Job {job.job_id} rejected for User {user.user_id}: Contains unwanted keywords.")
                return False

            # If all checks pass
            return True
            
        except Exception as e:
            logger.error(f"Error filtering job {job.job_id} for user {user.user_id}: {e}")
            # Fail closed: if something breaks during evaluation, skip this job 
            # for this user rather than sending them a broken/unwanted notification.
            return False