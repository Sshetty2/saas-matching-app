import logging
from graph.workflow_state import WorkflowState
from logging_config import log_execution_time
from database.connection import get_pyodbc_connection, wrap_query_with_json_instructions
import json
from config import settings

logger = logging.getLogger(__name__)

cpe_table_name = settings.db.db_table

vendor_and_product_query = (
    f"SELECT * FROM {cpe_table_name} WHERE product LIKE ? AND vendor LIKE ?"
)
product_query = f"SELECT * FROM {cpe_table_name} WHERE product LIKE ?"
vendor_query = f"SELECT * FROM {cpe_table_name} WHERE vendor LIKE ?"


def execute_query(query, params, query_type, db_connection):
    logger.info(
        f"Executing query: {query} with params: {params} and query_type: {query_type}"
    )
    cursor = db_connection.cursor()
    query = wrap_query_with_json_instructions(query)
    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()
    results = results[0][0] if results else None
    if results:
        return json.loads(results)
    else:
        return None


def query_database(state: WorkflowState) -> WorkflowState:
    results = None

    attempts = 1

    software_alias = state.get("software_alias", "")
    software_info = state.get("software_info", {})
    product = software_info.get("product", "")
    vendor = software_info.get("vendor", "")
    version = software_info.get("version", "")

    query_type = None

    db_connection = get_pyodbc_connection()

    with log_execution_time(
        logger,
        f"Querying Database for {software_alias}",
    ):
        try:

            while not results and attempts <= 3:
                if attempts == 1:
                    if not product or product == "N/A" or not vendor or vendor == "N/A":
                        attempts += 1
                        continue
                    query_type = "vendor_and_product"
                    results = execute_query(
                        vendor_and_product_query,
                        (f"%{product}%", f"%{vendor}%"),
                        query_type,
                        db_connection,
                    )
                elif attempts == 2:
                    if not product or product == "N/A":
                        attempts += 1
                        continue
                    query_type = "product"
                    results = execute_query(
                        product_query, (f"%{product}%"), query_type, db_connection
                    )
                elif attempts == 3:
                    if not vendor or vendor == "N/A":
                        attempts += 1
                        continue
                    query_type = "vendor"
                    results = execute_query(
                        vendor_query, (f"%{vendor}%"), query_type, db_connection
                    )
                if results:
                    break
                attempts += 1
        except Exception as e:
            logger.error(f"Failed to fetch results for alias: {software_alias}; {e}")
            return {"__end__": True, **state, "error": str(e)}

        if results:
            logger.info(
                f"Successfully queried CPE Database for {software_alias} with {len(results)} records"
            )
            return {**state, "cpe_results": results}
        else:
            logger.info(
                f"No results found from CPE Database for alias: {software_alias}"
            )
            return {
                "__end__": True,
                **state,
                "match_type": "No Match",
                "info": "No results found from CPE Database",
            }
