"""
===============================================================================
CORE AI & PROCESSING ENGINE (comp_engine.py)
===============================================================================

OVERVIEW:
This module serves as the central intelligence and data management layer of the 
Freelance Hunter architecture. It encapsulates all database interactions (SQLite, 
ChromaDB) and AI evaluations (SentenceTransformers, Groq LLM), acting as a unified 
interface for the rest of the application.

SYSTEM ARCHITECTURE & DATA FLOW:
The engine acts as the intermediary bridging the data collection (Scraper) and 
user interface (Telegram Bot) components. The standard execution flow is as follows:

1. User Registration Flow:
   Telegram Bot receives user preferences -> Passes data to Engine (`register_or_update_user`) 
   -> Engine generates vector embeddings and stores the profile in databases.

2. Job Matching Flow:
   Web Scraper fetches a raw job post -> Passes job to Engine (`process_new_job`)
   -> Engine performs rule-based filtering, vector similarity search, and LLM evaluation
   -> Engine returns validated matches -> Telegram Bot dispatches notifications to users.

INTEGRATION INSTRUCTIONS (main.py):
To integrate this engine into the main application entry point, adhere to the 
following initialization sequence:

1. Instantiate the Engine:
   engine = FreelanceHunterEngine()

2. Initialize Databases (CRITICAL - Must await before starting other services):
   await engine.initialize()

3. Dependency Injection:
   Pass the `engine` instance to the initialization loops of both the Scraper 
   and the Telegram Bot. Run both services concurrently using `asyncio.gather()`.
===============================================================================
"""



import asyncio
import logging
from typing import List, Tuple

from models.schemas import JobPost, UserPreferences, LLMResponse
from database.relational_db import RelationalDB
from database.vector_db import VectorDB
from ai_engine.embedder import Embedder
from ai_engine.filter import RuleBasedFilter
from ai_engine.llm_evaluator import LLMEvaluator

# Global logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

class FreelanceHunterEngine:
    """
    The core AI and job processing engine for the Freelance Hunter Bot.
    This class encapsulates all databases, ML models, and API integrations,
    exposing a clean and simple interface for the Scraper and Telegram Bot.
    """
    
    def __init__(self):
        # Instantiate all sub-modules. The ML model (SentenceTransformers) 
        # is loaded into RAM only once here.
        self.relational_db = RelationalDB()
        self.vector_db = VectorDB()
        self.embedder = Embedder()
        self.llm_evaluator = LLMEvaluator()

    async def initialize(self) -> None:
        """
        Must be called once during the application startup phase.
        Ensures all necessary database tables exist before processing begins.
        """
        logger.info("Initializing Freelance Hunter AI Engine...")
        await self.relational_db.initialize_database()
        logger.info("Engine initialized successfully.")

    async def register_or_update_user(self, user_data: UserPreferences) -> bool:
        """
        To be called by the Telegram Bot UI.
        Whenever a user registers or updates their settings (budget, skills, bio),
        pass the structured UserPreferences object here.
        
        Args:
            user_data: The Pydantic model containing the user's profile.
            
        Returns:
            bool: True if registration was successful, False otherwise.
        """
        try:
            logger.info(f"Registering/Updating user {user_data.user_id}...")
            
            # 1. Save standard settings to SQLite
            await self.relational_db.upsert_user(user_data)
            
            # 2. Convert the user's text resume/bio into a mathematical vector
            embedding = await self.embedder.generate_embedding(user_data.resume_text)
            
            # 3. Store the vector in ChromaDB for fast similarity search later
            await self.vector_db.upsert_user_resume(user_data.user_id, embedding, user_data.resume_text)
            
            logger.info(f"User {user_data.user_id} registered perfectly.")
            return True
        except Exception as e:
            logger.error(f"Failed to register user {user_data.user_id}: {e}")
            return False

    async def process_new_job(self, job: JobPost) -> List[Tuple[int, LLMResponse]]:
        """
        To be called by the Web Scraper / Telegram Channel Monitor.
        Pass the raw scraped job here. The engine will evaluate it against all 
        registered tenants (users) and return a list of successful matches.
        
        Args:
            job: The raw scraped job encapsulated in the JobPost Pydantic model.
            
        Returns:
            List[Tuple[int, LLMResponse]]: A list of tuples. 
            Format: (telegram_user_id, structured_llm_response_for_the_bot)
        """
        notifications_to_send = []
        
        # 1. Deduplication: Skip if we have already evaluated this exact job ID
        if await self.relational_db.is_job_processed(job.job_id, job.source):
            return notifications_to_send

        logger.info(f"Processing new job: {job.title} ({job.job_id})")

        # 2. Fetch all active tenants (users) from the database
        users = await self.relational_db.get_all_users()
        
        # Temporary variable to hold the job embedding (Lazy Loading optimization)
        job_embedding = None

        for user in users:
            # 3. Rule-Based Filter: Cheap, fast checks (budget, negative keywords)
            if not await RuleBasedFilter.evaluate(job, user):
                continue
            
            # We only generate the job embedding if it actually passes the basic rules 
            # for at least ONE user. This saves massive CPU resources.
            if job_embedding is None:
                job_embedding = await self.embedder.generate_embedding(job.description)
            
            # 4. Vector Search: Compare job requirements against the user's resume
            similarity = await self.vector_db.check_similarity(user.user_id, job_embedding)
            if similarity < user.similarity_threshold:
                continue
            
            # 5. LLM Evaluation: Final strict check using Groq/Llama-3
            logger.info(f"Job {job.job_id} looks good for {user.user_id}. Asking LLM...")
            llm_result = await self.llm_evaluator.evaluate_job(job, user)
            
            # If the LLM validates the match, append it to the outgoing queue
            if llm_result:
                notifications_to_send.append((user.user_id, llm_result))
                
        return notifications_to_send

