"""Database connection utilities."""

import os
import pyodbc
from langchain_community.utilities import SQLDatabase
from config import settings


def wrap_query_with_json_instructions(query):
    return f"SELECT (({query} FOR JSON AUTO)) AS json"


def build_connection_string():
    """Build and return the connection string based on environment variables."""

    connection_params = [
        "DRIVER={ODBC Driver 17 for SQL Server}",
        f"SERVER={settings.db.db_server}",
        f"DATABASE={settings.db.db_name}",
    ]

    if settings.db.db_user and settings.db.db_password:
        connection_params.extend(
            [
                f"UID={settings.db.db_user}",
                f"PWD={settings.db.db_password.get_secret_value()}",
            ]
        )
    else:
        connection_params.append("Trusted_Connection=yes")

    return ";".join(connection_params)


def get_pyodbc_connection():
    """Get a raw database connection using the appropriate connection string."""
    connection_string = build_connection_string()

    return pyodbc.connect(connection_string)
