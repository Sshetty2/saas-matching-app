# from graph.workflow import run_workflows_parallel

# from store.load_vector_store import load_vector_store
from sentence_transformers import SentenceTransformer
import redis
from redis.commands.search.query import Query
import numpy as np
from config import settings
import asyncio


# Initialize event loop before other imports to prevent
# "There is no current event loop in thread" errors,
# particularly when running in Docker
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Commented out original code
# if __name__ == "__main__":
#     result = asyncio.run(
#         run_workflows_parallel(
#             [
#                 "Microsoft Visual C++ 2008 Redistributable - x86 9.0.30729.4974",
#             ]
#         )
#     )


redis_host = settings.redis.host
redis_port = settings.redis.port
redis_db = settings.redis.db


async def test_redis_vector_search():
    # Initialize the model and Redis client
    model = SentenceTransformer(settings.llm.embedding_model, truncate_dim=512)
    redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

    # Query to search for
    query = "search_query: apache_tomcat"
    print(f"Searching for: {query}")

    # Encode the query
    query_embedding = model.encode([query])[0].astype(np.float32).tobytes()

    # Create a vector query using the proper Redis-py syntax
    query = (
        Query("*=>[KNN 3 @embedding $query_vector AS score]")
        .sort_by("score")
        .dialect(2)
        .return_fields("metadata", "score", "vendor", "product")
    )

    # Execute the search with the query vector
    search_result = redis_client.ft("product_index").search(
        query,
        query_params={"query_vector": query_embedding},
    )

    print(f"Search results: {search_result}")

    # Parse and display results in a more readable format
    if search_result.total > 0:
        print(f"Found {search_result.total} matches:")
        for i, doc in enumerate(search_result.docs):
            print(f"Match {i+1}:")
            print(f"  Key: {doc.id}")
            print(f"  Score: {doc.score}")
            print(f"  Vendor: {doc.vendor}")
            print(f"  Product: {doc.product}")

    else:
        print("No matches found")


if __name__ == "__main__":
    asyncio.run(test_redis_vector_search())
