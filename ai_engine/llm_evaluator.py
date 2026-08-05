import json
import logging
from typing import Optional

from groq import AsyncGroq, APIError
from pydantic import ValidationError

from models.schemas import JobPost, UserPreferences, LLMResponse
from config.settings import settings

logger = logging.getLogger(__name__)

class LLMEvaluator:
    """
    Asynchronous evaluator that uses the Groq API (Llama-3) to score 
    the match between a job post and a user's profile.
    """

    def __init__(self, model_name: str = "llama-3.3-70b-versatile"):
        self.model_name = model_name
        try:
            # Explicitly pass the API key from our settings
            self.client = AsyncGroq(api_key=settings.groq_api_key)
            logger.info(f"AsyncGroq client initialized with model: {self.model_name}")
        except Exception as e:
            logger.critical(f"Failed to initialize AsyncGroq client: {e}")
            raise

    def _build_system_prompt(self) -> str:
        """
        Constructs a strict system prompt that forces the LLM to act as a 
        recruiter and strictly output JSON matching our Pydantic schema.
        """
        schema = LLMResponse.model_json_schema()
        
        return (
            "You are an expert technical recruiter and AI matchmaker. "
            "Your task is to evaluate how well a specific job post matches a candidate's profile. "
            "You must respond ONLY with valid JSON. Do not include any markdown formatting, "
            "preambles, or conversational text. Your output must strictly adhere to the "
            f"following JSON Schema:\n\n{json.dumps(schema, indent=2)}"
        )

    def _build_user_prompt(self, job: JobPost, user: UserPreferences) -> str:
        """
        Constructs the user prompt containing the tenant's profile and the job data.
        """
        return (
            f"--- CANDIDATE PROFILE ---\n"
            f"Core Skills: {', '.join(user.preferred_skills)}\n"
            f"Resume/Bio:\n{user.resume_text}\n\n"
            f"--- JOB POST ---\n"
            f"Title: {job.title}\n"
            f"Source: {job.source}\n"
            f"Description:\n{job.description}\n\n"
            "Evaluate the match, calculate a score (0-100), extract the top 3 reasons "
            "why it is a good fit, and write a catchy one-line summary tailored to the candidate."
        )

    async def evaluate_job(self, job: JobPost, user: UserPreferences) -> Optional[LLMResponse]:
        """
        Asynchronously sends the evaluation task to the Groq API.
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(job, user)

        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model_name,
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=500
            )

            raw_content = response.choices[0].message.content
            
            if not raw_content:
                logger.warning(f"Groq API returned empty content for Job {job.job_id} / User {user.user_id}")
                return None

            validated_response = LLMResponse.model_validate_json(raw_content)
            logger.info(f"Successfully evaluated Job {job.job_id} for User {user.user_id} (Score: {validated_response.match_score})")
            
            return validated_response

        except APIError as e:
            logger.error(f"Groq API Error evaluating job {job.job_id} for user {user.user_id}: {e}")
            return None
        except ValidationError as e:
            logger.error(f"LLM output failed Pydantic validation for job {job.job_id}: {e}\nRaw output: {raw_content}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during LLM evaluation: {e}")
            return None