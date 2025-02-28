import os
from sentence_transformers import SentenceTransformer
from graph.workflow_state import WorkflowState
from graph.workflow_state import AnalysisResult
from sklearn.metrics.pairwise import cosine_similarity
from store.load_vector_store import load_vector_store
import numpy as np
import logging
from logging_config import log_execution_time
from langchain_core.documents import Document
from thefuzz import fuzz

logger = logging.getLogger(__name__)

use_vector_store = os.getenv("USE_VECTOR_STORE", "True").lower() == "true"

if use_vector_store:
    with log_execution_time(logger, "Loading Vector Store"):
        vector_store = load_vector_store()


def check_fuzz_score(str_to_check, str_to_compare, score_threshold):
    if str_to_compare == "":
        return True
    else:
        return fuzz.ratio(str_to_check, str_to_compare) > score_threshold


async def search_with_vendor_filter(query: str, vendor: str, product: str, k: int = 3):
    """Search for documents with a specific vendor."""

    vendor_name = vendor.lower()
    product_name = product.lower()

    def vendor_filter(doc: Document) -> bool:
        """Filter documents by vendor name in metadata."""
        doc_vendor = doc.metadata.get("vendor", "")
        doc_product = doc.metadata.get("product", "")
        doc_vendor = doc_vendor.lower()
        doc_product = doc_product.lower()

        passes_vendor_filter = check_fuzz_score(doc_vendor, vendor_name, 60)
        passes_product_filter = check_fuzz_score(doc_product, product_name, 60)

        return passes_vendor_filter and passes_product_filter

    results = await vector_store.asimilarity_search_with_score(
        query, k=k, filter=vendor_filter
    )

    return results


async def find_matches(state: WorkflowState) -> WorkflowState:
    if use_vector_store:
        return await find_matches_with_vector_store(state)
    else:
        return await find_matches_without_vector_store(state)


async def find_matches_with_vector_store(state):
    """Get top 3 best CPE matches for a given software configuration."""

    with log_execution_time(logger, "Finding Matches"):
        software_alias = state.get("software_alias", "")
        vendor = state.get("software_info", {}).get("vendor", "")
        product = state.get("software_info", {}).get("product", "")

        if vendor == "" and product == "":
            logger.error(f"No vendor or product found for {software_alias}")
            return {
                "__end__": True,
                **state,
                "match_type": "No Match",
                "info": "No vendor or product found for the given software alias.",
            }

        doc_results = await search_with_vendor_filter(
            software_alias, vendor, product, 3
        )

        if not doc_results:
            logger.error(f"No CPE records found for {software_alias}")
            return {
                **state,
                "match_type": "No Match",
                "info": "No CPE records found for the given software alias.",
            }

        top_matches = [doc.page_content for doc, score in doc_results]

    logger.info(f"Top 3 CPE Matches: {top_matches}")

    return {**state, "top_matches": top_matches}


async def find_matches_without_vector_store(state):
    """Get top 3 best CPE matches for a given software alias"""
    software_alias = state.get("software_alias", "")
    cpe_results = state.get("cpe_results", [])

    logger.info(f"Finding top 3 CPE Matches for alias: {software_alias}")

    if not cpe_results:
        logger.info("No CPE results found")
        return {
            "__end__": True,
            **state,
            "match_type": "No Match",
            "info": "No CPE results found from the database",
        }

    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")

        cpe_texts = [cpe["ConfigurationsName"] for cpe in cpe_results]

        encoded_query = model.encode([software_alias])
        encoded_results = model.encode(cpe_texts)

        similarities = cosine_similarity(encoded_query, encoded_results).flatten()

        ranked_results = sorted(
            zip(cpe_results, similarities), key=lambda x: x[1], reverse=True
        )

        top_matches = ranked_results[:3]
        logger.info(f"Top 3 CPE Matches for {software_alias}: {top_matches}")

    except Exception as e:
        logger.error(f"Error finding matches for alias: {software_alias}; {e}")
        return {**state, "error": str(e)}

    return {**state, "top_matches": top_matches}
