import asyncio
import logging
from typing import List

import chromadb
from chromadb.config import Settings as ChromaSettings
from config.settings import settings

logger = logging.getLogger(__name__)

class VectorDB:
    """
    Handles asynchronous interactions with ChromaDB to store user resume embeddings 
    and compute similarity scores against incoming job posts.
    """

    def __init__(self, db_path: str = settings.chroma_db_path):
        try:
            self.client = chromadb.PersistentClient(path=db_path)
            self.collection = self.client.get_or_create_collection(
                name="user_resumes",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB initialized and 'user_resumes' collection ready.")
        except Exception as e:
            logger.critical(f"Failed to initialize ChromaDB: {e}")
            raise

    def _upsert_user_sync(self, user_id: int, embedding: List[float], resume_text: str) -> None:
        """Synchronous method to upsert a user's resume vector."""
        self.collection.upsert(
            ids=[str(user_id)],
            embeddings=[embedding],
            documents=[resume_text],
            metadatas=[{"user_id": user_id}]
        )

    async def upsert_user_resume(self, user_id: int, embedding: List[float], resume_text: str) -> None:
        """
        Asynchronously stores or updates a user's resume embedding in ChromaDB.
        """
        try:
            await asyncio.to_thread(self._upsert_user_sync, user_id, embedding, resume_text)
            logger.info(f"Successfully upserted vector for user {user_id}.")
        except Exception as e:
            logger.error(f"Error upserting vector for user {user_id}: {e}")
            raise

    def _get_similarity_sync(self, user_id: int, job_embedding: List[float]) -> float:
        """
        Synchronous method to query ChromaDB for a specific user's distance to a job vector.
        """
        results = self.collection.query(
            query_embeddings=[job_embedding],
            where={"user_id": user_id},
            n_results=1
        )
        
        if not results.get("distances") or not results["distances"][0]:
            logger.warning(f"No vector found for user {user_id} during similarity check.")
            return 0.0
            
        distance = results["distances"][0][0]
        similarity = 1.0 - distance
        return similarity

    async def check_similarity(self, user_id: int, job_embedding: List[float]) -> float:
        """
        Asynchronously compares a job's vector against a specific user's stored resume vector.
        """
        try:
            similarity = await asyncio.to_thread(self._get_similarity_sync, user_id, job_embedding)
            return similarity
        except Exception as e:
            logger.error(f"Error calculating similarity for user {user_id}: {e}")
            return 0.0