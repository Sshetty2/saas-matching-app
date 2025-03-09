from sentence_transformers import SentenceTransformer
from config import settings
from redis.commands.search.query import Query
from redis import Redis
import numpy as np
from textwrap import dedent
from pydantic import BaseModel
from thefuzz import fuzz
from typing import List
from logging_config import log_execution_time, configure_logging
from graph.workflow_state import WorkflowState
from graph.get_ai_client import get_ai_client
from graph.format_utils import format_product_matches, format_software_info

logger = configure_logging()

embedding_model_name = settings.llm.embedding_model

redis_host = settings.redis.host
redis_port = settings.redis.port
redis_db = settings.redis.db

redis_client = Redis(host=redis_host, port=redis_port, db=redis_db)
embedding_model = SentenceTransformer(embedding_model_name, truncate_dim=512)


def sort_search_results_by_vendor_similarity(docs, vendor):
    """Sorts search results by vendor fuzzy match first, then by vector similarity score."""

    ranked_results = []

    for doc in docs:
        doc_vendor = doc.vendor
        vendor_fuzz_score = fuzz.ratio(vendor, doc_vendor)

        ranked_results.append(
            {
                "doc": doc,
                "vendor_fuzz_score": vendor_fuzz_score,
                "vector_score": doc.score,
            }
        )

    ranked_results.sort(key=lambda x: (-x["vendor_fuzz_score"], x["vector_score"]))

    return [item["doc"] for item in ranked_results]


def check_fuzz_score(a, b, score_threshold):
    if b == "" or a == "":
        return True
    else:
        return fuzz.ratio(a, b) > score_threshold


class ProductMatchPydantic(BaseModel):
    matched_products: List[str]


system_prompt = dedent(
    """
    We are attempting to find matches in a database based on a software alias after it has been parsed and a vector search has been performed. 
    Your role is to analyze the original software alias and parsed software info and determine if any of the product matches are actually valid.

    ### Task Instructions:
    1. Compare the original software alias and parsed software info with the top product matches after a vector search.
    2. Evaluate whether the vendor and product names match logically to the software alias and / or parsed software info.
    3. If a match is valid, add it to the **final list of matched products**.

    NOTE: Many product names may include 'escape' or 'special' characters and the product name should be returned as is. 
    There may be semantic differences but the product would still be a valid match.
    The parsed software info may not be 100% accurate and finding a match based on the software alias is more important.

    ### JSON Output Format:
    Please return a **valid JSON object** with an array of the product match numbers from the vector search.

    ```json
    {
        "matched_products": ["1", "3", "5"]
    }
    ```
    """
)


user_prompt = dedent(
    """
    ### Software Alias to Match:
    "{software_alias}"

    ### Parsed Software Info:
    {software_info}

    ### Top 3 Closest Product Matches (Vector Search Results):
    {formatted_matches}

    ### Task:
    Analyze the above data and return a JSON object listing valid product matches.

    **Return only JSON. No extra explanations.**
    """
)


async def find_product_matches(state: WorkflowState):
    """
    Uses the parse results in order to find vendor and product matches based on what's in the database
    """
    software_alias = state.get("software_alias", "")
    software_info = state.get("software_info", {})
    vendor = software_info.get("vendor", "")
    product = software_info.get("product", "")

    search_query = f"search_query: {product}"
    query_embedding = (
        embedding_model.encode([search_query])[0].astype(np.float32).tobytes()
    )

    # current design expects product to be found first;
    # TODO item could be searching for top vendors then products given vendor if there is no good product match

    # return top matches for given product
    query = (
        Query("*=>[KNN 10 @embedding $query_vector AS score]")
        .sort_by("score")
        .dialect(2)
        .return_fields("metadata", "score", "vendor", "product")
    )

    search_results = redis_client.ft("product_index").search(
        query,
        query_params={"query_vector": query_embedding},
    )

    # if the first search based on the parsed product name returns no results, try searching based on the software alias
    if search_results.total == 0:
        search_query = f"search_query: {software_alias.lower()}"
        query_embedding = (
            embedding_model.encode([search_query])[0].astype(np.float32).tobytes()
        )

        search_results = redis_client.ft("product_index").search(
            query,
            query_params={"query_vector": query_embedding},
        )

        if search_results.total == 0:
            return {**state, "info": "Vector search returned no results"}

    sorted_search_results = sort_search_results_by_vendor_similarity(
        search_results.docs, vendor
    )

    product_search_results = [
        {"product": doc.product, "vendor": doc.vendor} for doc in sorted_search_results
    ]

    formatted_user_prompt = user_prompt.format(
        software_alias=software_alias,
        software_info=format_software_info(software_info),
        formatted_matches=format_product_matches(product_search_results),
    )

    completion_function, model_args, parse_response_function = get_ai_client(
        ProductMatchPydantic, system_prompt, formatted_user_prompt
    )

    with log_execution_time(logger, f"Finding Product Matches for {software_alias}"):
        try:
            response = await completion_function(**model_args)
            result = parse_response_function(response, ProductMatchPydantic)
        except Exception as e:
            logger.error(
                f"Error finding vendor product matches for {software_alias}: {e}"
            )
            return {
                **state,
                "error": str(e),
                "info": "Error finding vendor product matches",
            }

    matched_products_indices = result.get("matched_products", [])

    if not matched_products_indices:
        return {
            **state,
            "info": "No product matches found",
        }

    matched_products_indices = [
        int(match_index) - 1 for match_index in matched_products_indices
    ]

    matched_products_indices.sort()

    last_index = matched_products_indices[-1]

    # handle case where incorrect index is returned
    if last_index >= len(product_search_results):
        return {
            **state,
            "info": "Incorrect index returned.",
        }

    matched_products = [
        product_search_results[match_index] for match_index in matched_products_indices
    ]

    if matched_products:
        return {
            **state,
            "product_search_results": product_search_results,
            "matched_products": matched_products,
        }
