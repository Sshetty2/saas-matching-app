import pyodbc
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    f"DATABASE={os.getenv('DB_DATABASE')};"
    "Trusted_Connection=yes;"
)

def get_connection():
    """Establish a database connection."""
    return pyodbc.connect(connection_string)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_computers():
    """Fetch distinct ComputerNames."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT ComputerName FROM tb_SaasInstalledAppsTemp ORDER BY ComputerName ASC")
        computers = [row[0] for row in cursor.fetchall()]
        conn.close()
        return computers
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return []

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_scan_ids(computer_name):
    """Fetch distinct ScanIDs for a selected ComputerName."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT ScanID 
        FROM tb_SaasInstalledAppsTemp 
        WHERE ComputerName = ? 
        ORDER BY ScanID DESC
    """, (computer_name,))
    scan_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return scan_ids

def get_installed_apps(computer_name, scan_id, limit=None):
    """Fetch applications for a given ComputerName and ScanID, with an optional limit."""
    conn = get_connection()
    cursor = conn.cursor()

    if limit and limit != "None":
        query = "SELECT TOP (?) ApplicationName FROM tb_SaasInstalledAppsTemp WHERE ComputerName = ? AND ScanID = ?"
        cursor.execute(query, (int(limit), computer_name, scan_id))
    else:
        query = "SELECT ApplicationName FROM tb_SaasInstalledAppsTemp WHERE ComputerName = ? AND ScanID = ?"
        cursor.execute(query, (computer_name, scan_id))

    apps = [row[0] for row in cursor.fetchall()]
    conn.close()
    return apps