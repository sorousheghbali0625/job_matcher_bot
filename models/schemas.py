from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class JobPost(BaseModel):
    """
    Represents a raw job post scraped from various platforms.
    This is the data contract expected from your friend's scraping module.
    """
    job_id: str = Field(
        ..., 
        description="Unique identifier for the job post (e.g., URL hash or platform-specific ID)."
    )
    source: str = Field(
        ..., 
        description="The platform where the job was found (e.g., 'Upwork', 'Telegram')."
    )
    title: str = Field(
        ..., 
        description="Job title or main headline."
    )
    description: str = Field(
        ..., 
        description="Full text description of the job requirements."
    )
    budget: Optional[float] = Field(
        default=None, 
        description="Parsed budget in USD. None if the budget is unlisted or variable."
    )
    url: Optional[str] = Field(
        default=None, 
        description="Link to the original job post."
    )
    posted_at: datetime = Field(
        default_factory=datetime.utcnow, 
        description="Timestamp of when the job was scraped or posted."
    )


class UserPreferences(BaseModel):
    """
    Represents a tenant (user) in our system, including their filtering 
    rules and context for vector/LLM matching.
    """
    user_id: int = Field(
        ..., 
        description="Unique identifier for the user (typically their Telegram ID)."
    )
    resume_text: str = Field(
        ..., 
        description="The user's resume, bio, or core skills used to generate their vector embedding."
    )
    min_budget: float = Field(
        default=0.0, 
        description="Minimum acceptable budget in USD. Jobs below this are filtered out."
    )
    unwanted_keywords: List[str] = Field(
        default_factory=list, 
        description="List of exact-match keywords that will instantly disqualify a job."
    )
    preferred_skills: List[str] = Field(
        default_factory=list, 
        description="Keywords representing the user's core stack (e.g., 'Python', 'React')."
    )
    similarity_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score (0.0 to 1.0) required to trigger LLM evaluation."
    )


class LLMResponse(BaseModel):
    """
    Strict JSON output schema enforced on the Groq API.
    """
    match_score: int = Field(
        ..., 
        ge=0, 
        le=100, 
        description="Score from 0 to 100 indicating how well the job fits the user's resume."
    )
    top_3_reasons: List[str] = Field(
        ..., 
        max_length=3,
        min_length=1,
        description="Up to 3 bullet points explaining why this is a good fit."
    )
    one_line_summary: str = Field(
        ..., 
        description="A short, catchy, one-line summary of the job tailored to the user."
    )