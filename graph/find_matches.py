from sentence_transformers import SentenceTransformer
from graph.workflow_state import WorkflowState
from sklearn.metrics.pairwise import cosine_similarity
from logging_config import log_execution_time, configure_logging
from config import settings

logger = configure_logging()

embedding_model_name = settings.llm.embedding_model


async def find_matches(state: WorkflowState) -> WorkflowState:
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
                    "Target_HW": cpe.get("Target_HW", ""),
                    "similarity_score": round(float(similarity), 2),
                }
                ranked_results.append(filtered_cpe)

            ranked_results.sort(key=lambda x: x["similarity_score"], reverse=True)

            top_matches = ranked_results[:5]

            for match in top_matches:
                if "similarity_score" in match:
                    del match["similarity_score"]

            logger.info(f"Top 3 CPE Matches for {software_alias}: {top_matches}")

        except Exception as e:
            logger.error(f"Error finding matches for alias: {software_alias}; {e}")
            return {**state, "error": str(e)}

    return {**state, "top_matches": top_matches}
