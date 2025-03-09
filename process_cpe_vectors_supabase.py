from database.connection import get_pyodbc_connection, wrap_query_with_json_instructions
from store.get_embedding_model import get_embedding_model
from logging_config import log_execution_time, configure_logging
from typing import Optional
from config import settings
import asyncio
from langchain_community.vectorstores import SupabaseVectorStore
from supabase.client import Client, create_client
import json

""" REDIS CURRENTLY IN USE FOR VECTOR STORE """

"""Will be used to process the CPE record vectors and save them to disk."""

"""This will need to run periodically to update the vector store."""

supabase_url = settings.db.supabase_url
supabase_key = settings.db.supabase_key
embedding_model_name = settings.llm.embedding_model

supabase: Client = create_client(supabase_url, supabase_key)

logger = configure_logging()

cpe_table_name = settings.db.db_table

db_connection = get_pyodbc_connection()


def get_cpe_records(prefix: Optional[str] = None):
    """Get the CPE records from the database."""

    logger.info(f"Getting CPE records")

    query = f"SELECT * FROM tb_CPEConfiguration"

    cursor = db_connection.cursor()
    query = wrap_query_with_json_instructions(query)
    cursor.execute(query)

    results = cursor.fetchall()
    cursor.close()
    results = results[0][0] if results else None
    if results:
        return json.loads(results)

    else:
        logger.error("No CPE records found in the database.")
        return None


async def process_cpe_vectors(prefix: Optional[str] = None):
    """Process the CPE record vectors and save them to disk."""

    is_default = not prefix

    with log_execution_time(
        logger, f"Processing CPE vectors for {"default" if is_default  else prefix}"
    ):
        cpe_records = get_cpe_records(prefix)

    if not cpe_records:
        logger.error("No CPE records found in the database.")
        return

    with log_execution_time(
        logger, f"Processing {len(cpe_records)} CPE vectors for vector store"
    ):
        try:

            cpe_texts = []
            metadata_records = []

            for cpe in cpe_records:

                cpeText = cpe["ConfigurationsName"]

                cpe_texts.append(cpeText)

                if not prefix:
                    metadata = cpe
                    metadata_records.append(metadata)

            total_records = len(cpe_texts)
            logger.info(f"Processing {total_records} CPE records")

            estimated_time_per_record = 0.00277
            total_estimated_time = total_records * estimated_time_per_record

            logger.info(
                f"Estimated processing time: {total_estimated_time:.2f} seconds"
            )

            embeddings = get_embedding_model()

            vector_store = SupabaseVectorStore(
                embedding=embeddings,
                client=supabase,
                table_name="documents",
                query_name="match_documents",
            )

            await vector_store.aadd_texts(cpe_texts, metadata_records)
        except Exception as e:
            logger.error(f"Error encoding CPE records: {e}")
            return


if __name__ == "__main__":
    asyncio.run(process_cpe_vectors())
