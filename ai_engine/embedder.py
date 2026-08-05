import asyncio
import logging
from typing import List, Union

# SentenceTransformers is imported locally inside the init to avoid 
# slow startup times if this module is imported but not immediately used.
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class Embedder:
    """
    Asynchronous wrapper for generating vector embeddings using SentenceTransformers.
    Designed to offload blocking CPU operations to a separate thread pool.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initializes the embedder. This should be instantiated ONLY ONCE during 
        app startup to keep the model weights loaded in memory.
        """
        logger.info(f"Loading SentenceTransformer model: {model_name}...")
        try:
            self.model = SentenceTransformer(model_name)
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.critical(f"Failed to load SentenceTransformer model: {e}")
            raise

    def _encode_sync(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Synchronous, blocking call to generate embeddings.
        Returns a flat list of floats for a single string, or a list of lists for multiple strings.
        """
        # encode() returns a numpy array. We convert it to standard python lists 
        # so it's compatible with Pydantic and ChromaDB out of the box.
        embeddings = self.model.encode(text, convert_to_numpy=True)
        return embeddings.tolist()

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Asynchronously generates an embedding for a single piece of text.
        """
        try:
            # asyncio.to_thread runs the blocking _encode_sync function in the 
            # default ThreadPoolExecutor, freeing the event loop to handle other users/jobs.
            embedding = await asyncio.to_thread(self._encode_sync, text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding for text (length {len(text)}): {e}")
            # Depending on how strict the pipeline is, you might want to raise here.
            # Returning an empty list signals upstream that embedding failed.
            return []

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Asynchronously generates embeddings for a batch of texts.
        Useful if we ever want to process multiple job posts at once.
        """
        try:
            embeddings = await asyncio.to_thread(self._encode_sync, texts)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings (batch size {len(texts)}): {e}")
            return []