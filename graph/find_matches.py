from sentence_transformers import SentenceTransformer
from graph.workflow_state import WorkflowState
from graph.workflow_state import AnalysisResult
from sklearn.metrics.pairwise import cosine_similarity
from store.load_vector_store import load_vector_store
import numpy as np
import logging
from logging_config import log_execution_time
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

with log_execution_time(logger, "Loading Vector Store"):
    vector_store = load_vector_store()


async def search_with_vendor_filter(query: str, vendor: str, k: int = 3):
    """Search for documents with a specific vendor."""

    vendor_name = vendor.lower()

    def vendor_filter(doc: Document) -> bool:
        """Filter documents by vendor name in metadata."""
        doc_vendor = doc.metadata.get("vendor", "")
        doc_vendor = doc_vendor.lower()

        return vendor_name in doc_vendor

    results = await vector_store.asimilarity_search_with_score(
        query, k=k, filter=vendor_filter
    )

    return results


async def find_matches(state: WorkflowState) -> WorkflowState:
    """Get top 3 best CPE matches for a given software configuration."""

    with log_execution_time(logger, "Finding Matches"):
        software_alias = state.get("software_alias", "")
        vendor = state.get("software_info", {}).get("vendor", "")

        doc_results = await search_with_vendor_filter(software_alias, vendor, 3)

        if not doc_results:
            logger.error(f"No CPE records found for {software_alias}")
            return {
                **state,
                "info": "No CPE records found for the given software alias.",
            }

        top_matches = [doc.page_content for doc, score in doc_results]

    logger.info(f"Top 3 CPE Matches: {top_matches}")

    return {**state, "top_matches": top_matches}
