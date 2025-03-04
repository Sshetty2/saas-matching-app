import os
from langchain_core.vectorstores import InMemoryVectorStore
from store.get_embedding_model import get_embedding_model
from store.save_vector_store import save_vector_store
from store.vector_path import get_vector_store_path
import traceback
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def load_vector_store(prefix: Optional[str] = None) -> InMemoryVectorStore:
    """Load the vector store from disk or create a new one."""
    logger.debug("Loading vector store")
    embeddings = get_embedding_model()

    vector_store_path = get_vector_store_path(prefix)

    if os.path.exists(vector_store_path):
        try:
            logger.info(f"Found existing vector store at {vector_store_path}")
            vs = InMemoryVectorStore.load(vector_store_path, embeddings)
            logger.info(
                f"Vector store loaded successfully with {len(vs.store)} documents"
            )
            return vs
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")

    logger.info("Creating new vector store")
    vs = InMemoryVectorStore(embedding=embeddings)
    save_vector_store(vs, vector_store_path)
    return vs
