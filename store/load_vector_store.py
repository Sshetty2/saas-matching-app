import os
from langchain_core.vectorstores import InMemoryVectorStore
from store.get_embedding_model import get_embedding_model
from store.save_vector_store import save_vector_store
from store.vector_path import VECTOR_STORE_PATH
import traceback
import logging


logger = logging.getLogger(__name__)


def load_vector_store() -> InMemoryVectorStore:
    """Load the vector store from disk or create a new one."""
    logger.debug("Loading vector store")
    embeddings = get_embedding_model()

    if os.path.exists(VECTOR_STORE_PATH):
        try:
            logger.info(f"Found existing vector store at {VECTOR_STORE_PATH}")
            vs = InMemoryVectorStore.load(VECTOR_STORE_PATH, embeddings)
            logger.info(
                f"Vector store loaded successfully with {len(vs.store)} documents"
            )
            return vs
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")

    logger.info("Creating new vector store")
    vs = InMemoryVectorStore(embedding=embeddings)
    save_vector_store(vs)
    return vs
