"""Database connection utilities."""

import os
import pyodbc
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv

load_dotenv()


def wrap_query_with_json_instructions(query):
    return f"SELECT (({query} FOR JSON AUTO)) AS json"


def build_connection_string():
    """Build and return the connection string based on environment variables."""

    connection_params = [
        "DRIVER={ODBC Driver 17 for SQL Server}",
        f"SERVER={os.getenv('DB_SERVER')}",
        f"DATABASE={os.getenv('DB_NAME')}",
    ]

    if os.getenv("DB_USER") and os.getenv("DB_PASSWORD"):
        connection_params.extend(
            [f"UID={os.getenv('DB_USER')}", f"PWD={os.getenv('DB_PASSWORD')}"]
        )
    else:
        connection_params.append("Trusted_Connection=yes")

    return ";".join(connection_params)


def get_pyodbc_connection():
    """Get a raw database connection using the appropriate connection string."""
    connection_string = build_connection_string()

    return pyodbc.connect(connection_string)
