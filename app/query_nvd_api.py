import os
import requests
import time
from dotenv import load_dotenv
import urllib.parse
from typing import Tuple, List, Dict, Union

load_dotenv()

last_request_time = 0
MIN_REQUEST_INTERVAL = 6

def query_nvd_api(software_name, api_key=None) -> Tuple[List, Dict[str, str]]:
    """Query NVD API for CPE matches with rate limiting.
    
    Args:
        software_name (str): Name of software to search
        api_key (str, optional): NVD API key for higher rate limits
        
    Returns:
        Tuple[List, Dict]: (products_list, error_info)
        - products_list: List of products found (empty if error)
        - error_info: Dictionary containing error details (empty if successful)
    """
    global last_request_time
    
    # Calculate time since last request
    current_time = time.time()
    time_since_last_request = current_time - last_request_time
    
    # If needed, wait until enough time has passed
    if time_since_last_request < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - time_since_last_request)
    
    base_url = "https://services.nvd.nist.gov/rest/json/cpes/2.0"
    
    # Prepare headers
    headers = {}
    if api_key:
        headers['apiKey'] = os.getenv("NVD_API_KEY")

    try:
        # Update last request time right before making the request
        last_request_time = time.time()
        query = urllib.parse.quote(software_name)
        response = requests.get(
            f"{base_url}?keywordSearch={query}",
            headers=headers
        )

        # Check for response status
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        return data.get("products", []), {}
        
    except requests.exceptions.HTTPError as e:
        error_info = {
            "software_name": software_name,
            "status_code": str(e.response.status_code),
            "error_message": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return [], error_info
        
    except requests.exceptions.RequestException as e:
        error_info = {
            "software_name": software_name,
            "status_code": "Unknown",
            "error_message": str(e),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        return [], error_info
