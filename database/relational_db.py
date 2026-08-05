import json
import logging
import sqlite3
from typing import List

import aiosqlite

from models.schemas import UserPreferences, JobPost
from config.settings import settings

logger = logging.getLogger(__name__)

class RelationalDB:
    """
    Handles asynchronous interactions with the SQLite database for managing 
    multi-tenant user profiles and deduplicating incoming job posts.
    """
    
    def __init__(self, db_path: str = settings.sqlite_db_path):
        self.db_path = db_path

    async def initialize_database(self) -> None:
        """
        Creates the necessary tables for users and jobs if they do not exist.
        Should be called once when the application starts.
        """
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            resume_text TEXT NOT NULL,
            min_budget REAL NOT NULL,
            unwanted_keywords TEXT NOT NULL,
            preferred_skills TEXT NOT NULL,
            similarity_threshold REAL NOT NULL
        );
        """
        
        create_jobs_table = """
        CREATE TABLE IF NOT EXISTS processed_jobs (
            job_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(create_users_table)
                await db.execute(create_jobs_table)
                await db.commit()
                logger.info("Database initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def is_job_processed(self, job_id: str, source: str) -> bool:
        """
        Checks if a job has already been processed to avoid spamming users
        or wasting LLM/Vector DB resources. If it hasn't been processed, 
        it marks it as processed.
        
        Returns:
            bool: True if the job was ALREADY processed, False if it is NEW.
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO processed_jobs (job_id, source) VALUES (?, ?)",
                    (job_id, source)
                )
                await db.commit()
                return False  # It was successfully inserted, so it is a new job
        except sqlite3.IntegrityError:
            return True
        except sqlite3.Error as e:
            logger.error(f"Database error while checking job {job_id}: {e}")
            return True 

    async def upsert_user(self, user: UserPreferences) -> None:
        """
        Inserts a new user or updates an existing user's preferences.
        """
        query = """
        INSERT INTO users (
            user_id, resume_text, min_budget, unwanted_keywords, preferred_skills, similarity_threshold
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            resume_text=excluded.resume_text,
            min_budget=excluded.min_budget,
            unwanted_keywords=excluded.unwanted_keywords,
            preferred_skills=excluded.preferred_skills,
            similarity_threshold=excluded.similarity_threshold;
        """
        
        unwanted_json = json.dumps(user.unwanted_keywords)
        skills_json = json.dumps(user.preferred_skills)
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    query, 
                    (
                        user.user_id, 
                        user.resume_text, 
                        user.min_budget, 
                        unwanted_json, 
                        skills_json, 
                        user.similarity_threshold
                    )
                )
                await db.commit()
                logger.info(f"User {user.user_id} upserted successfully.")
        except sqlite3.Error as e:
            logger.error(f"Failed to upsert user {user.user_id}: {e}")
            raise

    async def get_all_users(self) -> List[UserPreferences]:
        """
        Retrieves all registered users to evaluate incoming job posts against.
        """
        query = "SELECT * FROM users"
        users = []
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query) as cursor:
                    async for row in cursor:
                        user = UserPreferences(
                            user_id=row["user_id"],
                            resume_text=row["resume_text"],
                            min_budget=row["min_budget"],
                            unwanted_keywords=json.loads(row["unwanted_keywords"]),
                            preferred_skills=json.loads(row["preferred_skills"]),
                            similarity_threshold=row["similarity_threshold"]
                        )
                        users.append(user)
            return users
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve users: {e}")
            return []