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

    # Exact match
    filtered_results = [
        record for record in cpe_results if record["Version"] == software_version
    ]

    if filtered_results:
        return filtered_results

    major_version, minor_version = extract_major_minor_version(software_version)

    # Major version match
    if not major_version:
        return cpe_results

    filtered_results = [
        record for record in cpe_results if record["Version"].startswith(major_version)
    ]

    # Minor version match first digit
    if filtered_results and minor_version:
        first_digit_minor = minor_version[0]
        filtered_results = [
            record
            for record in filtered_results
            if re.match(rf"^{major_version}\.{first_digit_minor}", record["Version"])
        ]

    if filtered_results:
        return filtered_results

    return cpe_results


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
        SELECT Product, Vendor, Version, ConfigurationsName, CPEConfigurationID, Updates, Edition
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

        if len(filtered_results) == 1 and version == filtered_results[0].get("Version"):
            return {
                **state,
                "exact_match": filtered_results[0].get("ConfigurationsName"),
                "info": "Exact match found",
            }

        return {
            **state,
            "cpe_results": filtered_results,
        }
