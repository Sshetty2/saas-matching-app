from langchain_core.vectorstores import InMemoryVectorStore
from store.vector_path import get_vector_store_path
from logging_config import configure_logging
from typing import Optional

logger = configure_logging()


def save_vector_store(vs: InMemoryVectorStore, path: Optional[str] = None):
    """Save the vector store to disk."""
    if not path:
        path = get_vector_store_path()
    try:
        logger.debug(f"Saving vector store with {len(vs.store)} documents")
        vs.dump(path)
        logger.info(f"Vector store saved successfully to {path}")
    except Exception as e:
        logger.error(f"Error saving vector store: {e}")
        logger.debug("Full traceback:", exc_info=True)
