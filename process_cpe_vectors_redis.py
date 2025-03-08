import json
import redis
import numpy as np
from database.connection import get_pyodbc_connection
from sentence_transformers import SentenceTransformer
from config import settings
from textwrap import dedent
from datetime import datetime
import argparse
from logging_config import configure_logging, log_execution_time
import os


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


redis_host = settings.db.redis_host
redis_port = settings.db.redis_port
redis_db = settings.db.redis_db

logger = configure_logging()
embedding_model_name = settings.llm.embedding_model
db_connection = get_pyodbc_connection()
table_name = settings.db.db_table

redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

BATCH_SIZE = 2000

CHECKPOINT_FILE = "cpe_processing_checkpoint.txt"


def process_cpe_vectors(mode):
    if mode not in ["vendor", "product"]:
        raise ValueError("Invalid mode. Please specify 'vendor' or 'product'.")

    is_vendor = mode == "vendor"
    db_property = "Vendor" if is_vendor else "Product"

    try:
        with open(CHECKPOINT_FILE, "r") as f:
            offset = int(f.read().strip())
            logger.info(f"Resuming from checkpoint at offset {offset}")
    except (FileNotFoundError, ValueError):
        offset = 0
        logger.info("Starting from beginning (offset 0)")

    model = SentenceTransformer(embedding_model_name, truncate_dim=512)

    cursor = db_connection.cursor()
    cursor.execute(f"SELECT COUNT(DISTINCT {db_property}) FROM {table_name}")
    total_records = cursor.fetchone()[0]
    logger.info(f"Total records to process: {total_records}")

    start_time = datetime.now()
    initial_offset = offset

    if is_vendor:
        select_query = f"SELECT DISTINCT Vendor"
    else:
        select_query = f"SELECT DISTINCT Vendor, Product"

    with log_execution_time(logger, "Processing CPE vectors for vector store"):
        while True:
            query = dedent(
                f"""
                {select_query}
                FROM {table_name}
                ORDER BY Vendor
                OFFSET {offset} ROWS
                FETCH NEXT {BATCH_SIZE} ROWS ONLY
                """
            )

            cursor = db_connection.cursor()
            cursor.execute(query)
            results = cursor.fetchall()

            if not results:
                logger.info("No more records to process")
                if os.path.exists(CHECKPOINT_FILE):
                    os.remove(CHECKPOINT_FILE)
                    logger.info(f"Removed checkpoint file {CHECKPOINT_FILE}")
                break

            columns = [column[0] for column in cursor.description]
            data = [dict(zip(columns, row)) for row in results]

            logger.info(f"Processing {len(data)} records after offset {offset}")

            search_documents = []
            cpe_data_item_by_id = {}

            for item in data:
                data_item = item.get(db_property, "unknown")
                search_document = f"search_document: {data_item}"

                search_documents.append(search_document)
                cpe_data_item_by_id[search_document] = item

            with log_execution_time(logger, "Encoding CPE vectors"):
                embeddings = model.encode(search_documents, prompt="passage")

            pipe = redis_client.pipeline()

            for i, search_document in enumerate(search_documents):
                item = cpe_data_item_by_id[search_document]
                data_item = item.get(db_property, "unknown")
                redis_key = f"{mode}:{data_item}"

                vendor = item.get("Vendor", "unknown")

                embedding = embeddings[i].astype(np.float32).tobytes()
                if is_vendor:
                    mapping = {
                        "vendor": data_item,
                        "embedding": embedding,
                    }
                else:
                    ## store both vendor and product for product mode
                    mapping = {
                        "product": data_item,
                        "vendor": vendor,
                        "embedding": embedding,
                    }

                pipe.hset(
                    redis_key,
                    mapping=mapping,
                )

            with log_execution_time(
                logger, f"Storing batch of {len(search_documents)} CPE vectors in Redis"
            ):
                pipe.execute()

            offset += BATCH_SIZE

            records_processed = offset - initial_offset
            elapsed_seconds = (datetime.now() - start_time).total_seconds()
            if records_processed > 0 and elapsed_seconds > 0:
                records_per_second = records_processed / elapsed_seconds
                remaining_records = total_records - offset
                estimated_seconds_remaining = remaining_records / records_per_second
                estimated_hours = estimated_seconds_remaining / 3600

                progress_percent = (offset / total_records) * 100
                logger.info(
                    f"Completed batch, new offset: {offset}/{total_records} "
                    f"({progress_percent:.2f}%) - "
                    f"Est. time remaining: {estimated_hours:.2f} hours"
                )
            else:
                logger.info(f"Completed batch, new offset: {offset}")

            with open(CHECKPOINT_FILE, "w") as f:
                f.write(str(offset))

    cursor.close()
    db_connection.close()
    logger.info("Processing complete")


parser = argparse.ArgumentParser(
    description="The prefix to process the CPE vectors for."
)

parser.add_argument(
    "--prefix", type=str, required=True, help="Specify 'vendor' or 'product'"
)

args = parser.parse_args()

prefix_value = args.prefix

if __name__ == "__main__":
    if prefix_value:
        process_cpe_vectors(prefix_value)
    else:
        process_cpe_vectors()
