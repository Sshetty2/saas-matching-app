from langchain_core.vectorstores import InMemoryVectorStore
from store.vector_path import VECTOR_STORE_PATH
import logging

logger = logging.getLogger(__name__)


def save_vector_store(vs: InMemoryVectorStore):
    """Save the vector store to disk."""
    try:
        logger.debug(f"Saving vector store with {len(vs.store)} documents")
        vs.dump(VECTOR_STORE_PATH)
        logger.info(f"Vector store saved successfully to {VECTOR_STORE_PATH}")
    except Exception as e:
        logger.error(f"Error saving vector store: {e}")
        logger.debug("Full traceback:", exc_info=True)
