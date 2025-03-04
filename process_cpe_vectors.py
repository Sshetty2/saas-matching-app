"""Will be used to process the CPE record vectors and save them to disk."""

"""This will need to run periodically to update the vector store."""


import os
from store.save_vector_store import save_vector_store
from store.vector_path import get_vector_store_path
from database.connection import get_pyodbc_connection, wrap_query_with_json_instructions
from langchain_community.vectorstores import InMemoryVectorStore
from logging_config import log_execution_time, configure_logging
from store.get_embedding_model import get_embedding_model
from typing import Optional
from config import settings
from tqdm import tqdm
import time
import argparse

import json
import logging


configure_logging()

logger = logging.getLogger(__name__)

cpe_table_name = settings.db.db_table

db_connection = get_pyodbc_connection()

distinct_product_query = f"SELECT DISTINCT Product FROM tb_CPEConfiguration"

distinct_vendor_query = f"SELECT DISTINCT Vendor FROM tb_CPEConfiguration"


def get_cpe_records(prefix: Optional[str] = None):
    """Get the CPE records from the database."""

    logger.info(
        f"Getting CPE records for {prefix}", extra={"prefix-true": prefix == "vendor"}
    )

    if prefix == "product":
        query = distinct_product_query
    elif prefix == "vendor":
        query = distinct_vendor_query
    else:
        query = f"SELECT * FROM tb_CPEConfiguration"

    cursor = db_connection.cursor()
    query = wrap_query_with_json_instructions(query)
    cursor.execute(query)

    logger.info(f"Query: {query}")
    results = cursor.fetchall()
    cursor.close()
    results = results[0][0] if results else None
    if results:
        return json.loads(results)

    else:
        logger.error("No CPE records found in the database.")
        return None


def process_cpe_vectors(prefix: Optional[str] = None):
    """Process the CPE record vectors and save them to disk."""

    is_default = not prefix

    with log_execution_time(
        logger, f"Processing CPE vectors for {"default" if is_default  else prefix}"
    ):
        cpe_records = get_cpe_records(prefix)

    if not cpe_records:
        logger.error("No CPE records found in the database.")
        return

    logger.info(f"Processing {len(cpe_records)} CPE vectors for vector store")

    with log_execution_time(
        logger, f"Processing {len(cpe_records)} CPE vectors for vector store"
    ):
        try:

            cpe_texts = []
            metadata_records = []

            for cpe in cpe_records:

                if prefix == "product":
                    cpeText = cpe["Product"]
                elif prefix == "vendor":
                    cpeText = cpe["Vendor"]
                else:
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

            embedding = get_embedding_model()
            vector_store = InMemoryVectorStore(embedding=embedding)

            batch_size = 512

            start_time = time.time()

            with tqdm(total=total_records, desc="Encoding CPE records") as pbar:
                for i in range(0, total_records, batch_size):
                    batch = cpe_texts[i : i + batch_size]

                    if not prefix:
                        metadata_batch = metadata_records[i : i + batch_size]
                        vector_store.add_texts(batch, metadata_batch)
                    else:
                        vector_store.add_texts(batch)

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

            vector_store_path = get_vector_store_path(prefix)

            with log_execution_time(logger, "Saving vector store to disk"):
                save_vector_store(vector_store, vector_store_path)

            total_time = time.time() - start_time
            logger.info(
                f"Completed processing {total_records} CPE records in {total_time:.2f} seconds "
                f"({total_time/total_records*1000:.2f} ms per record)"
            )

        except Exception as e:
            logger.error(f"Error encoding CPE records: {e}")
            return


parser = argparse.ArgumentParser(
    description="The prefix to process the CPE vectors for."
)

parser.add_argument(
    "--prefix", type=str, required=False, help="Specify 'vendor' or 'product'"
)

args = parser.parse_args()

prefix_value = args.prefix

if __name__ == "__main__":
    if prefix_value:
        process_cpe_vectors(prefix_value)
    else:
        process_cpe_vectors()
