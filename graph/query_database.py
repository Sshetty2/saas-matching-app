from graph.workflow_state import WorkflowState
from logging_config import log_execution_time, configure_logging
from database.connection import get_pyodbc_connection
from config import settings
import re

logger = configure_logging()

cpe_table_name = settings.db.db_table


def extract_major_minor_version(version):
    """Extracts major and minor version numbers from a version string."""
    match = re.match(r"(\d+)(?:\.(\d+))?", version)  # Matches `X` or `X.Y`
    if match:
        major = match.group(1)
        minor = match.group(2) if match.group(2) else None
        return major, minor
    return None, None


def filter_cpe_results(cpe_results, software_version):
    """Filters CPE records based on major and minor version constraints."""

    major_version, minor_version = extract_major_minor_version(software_version)

    if not major_version or len(cpe_results) < 50:
        return cpe_results

    filtered_results = [
        record for record in cpe_results if record["Version"].startswith(major_version)
    ]

    if len(filtered_results) > 100 and minor_version:
        first_digit_minor = minor_version[0]
        filtered_results = [
            record
            for record in filtered_results
            if re.match(rf"^{major_version}\.{first_digit_minor}", record["Version"])
        ]

    return filtered_results


def execute_query(query, params, db_connection):
    cursor = db_connection.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    data = [dict(zip(columns, row)) for row in results]
    cursor.close()
    return data


def query_database(state: WorkflowState) -> WorkflowState:
    results = None

    matched_products = state.get("matched_products", [])

    if not matched_products:
        return state

    matched_products_without_vendor = [
        product_dict.get("product") for product_dict in matched_products
    ]

    software_alias = state.get("software_alias", "")
    software_info = state.get("software_info", {})
    version = software_info.get("version", "")
    placeholders = ", ".join(["?"] * len(matched_products_without_vendor))

    query = f"""
        SELECT Product, Vendor, Version, ConfigurationsName, CPEConfigurationID
        FROM tb_CPEConfiguration
        WHERE Product IN ({placeholders})
    """

    db_connection = get_pyodbc_connection()

    with log_execution_time(
        logger,
        f"Querying Database for {software_alias} matched products: {matched_products_without_vendor}",
    ):

        results = execute_query(query, matched_products_without_vendor, db_connection)

        logger.info(f"Found {len(results)} results")

        filtered_results = filter_cpe_results(results, version)

        logger.info(
            f"Queried CPE Database for {software_alias} and matched products: {matched_products_without_vendor} with {len(filtered_results)} filtered records"
        )

        return {
            **state,
            "cpe_results": filtered_results,
        }
