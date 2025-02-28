"""Will be used to process the CPE record vectors and save them to disk."""

"""This will need to run periodically to update the vector store."""


import os
from dotenv import load_dotenv
from store.save_vector_store import save_vector_store
from database.connection import get_pyodbc_connection, wrap_query_with_json_instructions
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import InMemoryVectorStore
from logging_config import log_execution_time, configure_logging
from langchain_huggingface import HuggingFaceEmbeddings
from store.get_embedding_model import get_embedding_model
from tqdm import tqdm
import time

import json
import logging

load_dotenv()

configure_logging()

logger = logging.getLogger(__name__)

cpe_table_name = os.getenv("CPE_TABLE_NAME")

db_connection = get_pyodbc_connection()


def get_cpe_records():
    """Get the CPE records from the database."""

    query = f"SELECT ConfigurationsName, Vendor FROM tb_CPEConfiguration"
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


def process_cpe_vectors():
    """Process the CPE record vectors and save them to disk."""

    with log_execution_time(logger, "Processing CPE vectors"):
        logger.info("Getting CPE records from the database")
        cpe_records = get_cpe_records()

    if not cpe_records:
        logger.error("No CPE records found in the database.")
        return

    with log_execution_time(logger, "Processing CPE vectors for vector store"):
        try:

            cpe_texts = []
            metadata_records = []

            for cpe in cpe_records:
                cpeText = cpe["ConfigurationsName"]
                cpe_texts.append(cpeText)
                vendor = cpe["Vendor"]
                metadata = {
                    "vendor": vendor,
                }
                metadata_records.append(metadata)

            total_records = len(cpe_texts)
            logger.info(f"Processing {total_records} CPE records")

            estimated_time_per_record = 0.00277
            total_estimated_time = total_records * estimated_time_per_record

            logger.info(
                f"Estimated processing time: {total_estimated_time:.2f} seconds"
            )

            embedding = get_embedding_model()
            vector_store = InMemoryVectorStore(embedding=embedding)

            batch_size = 512

            start_time = time.time()

            with tqdm(total=total_records, desc="Encoding CPE records") as pbar:
                for i in range(0, total_records, batch_size):
                    batch = cpe_texts[i : i + batch_size]
                    metadata_batch = metadata_records[i : i + batch_size]
                    vector_store.add_texts(batch, metadata_batch)
                    pbar.update(len(batch))

                    if (i + batch_size) % 5000 == 0 or (
                        i + batch_size
                    ) >= total_records:
                        elapsed = time.time() - start_time
                        records_processed = min(i + batch_size, total_records)
                        percentage = (records_processed / total_records) * 100
                        logger.info(
                            f"Progress: {percentage:.1f}% ({records_processed}/{total_records}) - "
                            f"Elapsed: {elapsed:.2f}s"
                        )

            logger.info("Saving vector store to disk")

            with log_execution_time(logger, "Saving vector store to disk"):
                save_vector_store(vector_store)

            total_time = time.time() - start_time
            logger.info(
                f"Completed processing {total_records} CPE records in {total_time:.2f} seconds "
                f"({total_time/total_records*1000:.2f} ms per record)"
            )

        except Exception as e:
            logger.error(f"Error encoding CPE records: {e}")
            return


if __name__ == "__main__":
    process_cpe_vectors()
