import os
from langchain_core.vectorstores import InMemoryVectorStore
from store.get_embedding_model import get_embedding_model
from store.save_vector_store import save_vector_store
from store.vector_path import get_vector_store_path
import traceback
from typing import Optional
from logging_config import configure_logging

logger = configure_logging()


def load_vector_store(prefix: Optional[str] = "default") -> InMemoryVectorStore:
    """Load the vector store from disk or create a new one."""
    logger.debug(f"Loading vector store for {prefix}")
    embeddings = get_embedding_model()

    vector_store_path = get_vector_store_path(prefix)

    if os.path.exists(vector_store_path):
        try:
            logger.info(f"Found existing vector store at {vector_store_path}")
            vs = InMemoryVectorStore.load(vector_store_path, embeddings)
            logger.info(
                f"Vector store loaded successfully with {len(vs.store)} documents for {prefix}"
            )
            return vs
        except Exception as e:
            logger.error(f"Error loading vector store for {prefix}: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")

    logger.info(f"Creating new vector store for {prefix}")
    vs = InMemoryVectorStore(embedding=embeddings)
    save_vector_store(vs, vector_store_path)
    return vs
