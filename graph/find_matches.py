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
from config import settings

logger = logging.getLogger(__name__)

use_vector_store = settings.execution.use_vector_store
embedding_model_name = settings.llm.embedding_model

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

    def vendor_product_filter(doc: Document) -> bool:
        """Filter documents by vendor name in metadata."""
        doc_vendor = doc.metadata.get("vendor", "")
        doc_product = doc.metadata.get("product", "")
        doc_vendor = doc_vendor.lower()
        doc_product = doc_product.lower()

        passes_vendor_filter = True
        passes_product_filter = True

        if doc_vendor != "" or doc_vendor == "N/A":
            passes_vendor_filter = check_fuzz_score(doc_vendor, vendor_name, 60)

        if doc_product != "" or doc_product == "N/A":
            passes_product_filter = check_fuzz_score(doc_product, product_name, 60)

        return passes_vendor_filter or passes_product_filter

    results = await vector_store.asimilarity_search_with_score(
        query, k=k, filter=vendor_product_filter
    )

    return results


async def find_matches(state: WorkflowState) -> WorkflowState:
    if use_vector_store:
        return await find_matches_with_vector_store(state)
    else:
        return await find_matches_without_vector_store(state)


async def find_matches_with_vector_store(state):
    """
    Get top 3 best CPE matches for a given software configuration using a vector store which needs to have been saved to disk prior to running this workflow.
    The vector store must be saved to disk prior to running this workflow with a manual operation. If the workflow should run without the vector store,
    set the USE_VECTOR_STORE environment variable to False.
    """
    software_alias = state.get("software_alias", "")

    logger.info(f"Finding top 3 CPE Matches for alias: {software_alias}")

    with log_execution_time(logger, "Finding Matches"):
        vendor = state.get("software_info", {}).get("vendor", "")
        product = state.get("software_info", {}).get("product", "")

        if vendor == "" and product == "" or vendor == "N/A" and product == "N/A":
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
    """
    Get top 3 best CPE matches for a given software alias using a database query.
    This workflow is slower than the one with the vector store because it embeds the cpe records at runtime.
    To use the vector store, set the USE_VECTOR_STORE environment variable to True and manually process cpe records to disk with process_cpe_records.py.
    """
    software_alias = state.get("software_alias", "")
    cpe_results = state.get("cpe_results", [])

    if not cpe_results:
        logger.info("No CPE results found")
        return {
            "__end__": True,
            **state,
            "match_type": "No Match",
            "info": "No CPE results found from the database",
        }

    logger.info(f"Finding top 3 CPE Matches for alias: {software_alias}")

    with log_execution_time(logger, f"Finding Matches for software: {software_alias}"):
        try:
            model = SentenceTransformer(embedding_model_name)

            cpe_texts = [cpe["ConfigurationsName"] for cpe in cpe_results]

            encoded_query = model.encode([software_alias])
            encoded_results = model.encode(cpe_texts)

            similarities = cosine_similarity(encoded_query, encoded_results).flatten()

            ranked_results = []
            for i, (cpe, similarity) in enumerate(zip(cpe_results, similarities)):
                filtered_cpe = {
                    "CPE_ID": cpe.get("ConfigurationsName", ""),
                    "Vendor": cpe.get("Vendor", ""),
                    "Product": cpe.get("Product", ""),
                    "Version": cpe.get("Version", ""),
                    "Updates": cpe.get("Updates", ""),
                    "Edition": cpe.get("Edition", ""),
                    "SW_Edition": cpe.get("SW_Edition", ""),
                    "Target_SW": cpe.get("Target_SW", ""),
                    "Target_HW": cpe.get("Target_HW", ""),
                    "similarity_score": round(float(similarity), 2),
                }
                ranked_results.append(filtered_cpe)

            ranked_results.sort(key=lambda x: x["similarity_score"], reverse=True)

            top_matches = ranked_results[:3]

            for match in top_matches:
                if "similarity_score" in match:
                    del match["similarity_score"]

            logger.info(f"Top 3 CPE Matches for {software_alias}: {top_matches}")

        except Exception as e:
            logger.error(f"Error finding matches for alias: {software_alias}; {e}")
            return {**state, "error": str(e)}

    return {**state, "top_matches": top_matches}
