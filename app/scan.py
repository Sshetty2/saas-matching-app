import pandas as pd
from database import get_installed_apps
from batch_process_requests import batch_process

def run_scan(computer_name, scan_id, limit):
    """
    Runs the scan:
    1. Fetches installed software for the selected ComputerName and ScanID.
    2. Calls `batch_process` to process the names.
    3. Returns results as a Pandas DataFrame.
    
    :param computer_name: Selected ComputerName
    :param scan_id: Selected ScanID
    :param limit: Maximum number of applications to process (int or "None").
    :return: Pandas DataFrame with scan results.
    """
    apps = get_installed_apps(computer_name, scan_id, limit)
    
    if not apps:
        return None

    batch_results = batch_process(apps)

    formatted_results = []
    for result in batch_results:
        best_match = result.get("best_match", None)
        
        formatted_results.append({
            "Query": result["query"],
            "Match Type": best_match["match_type"] if best_match else "No Match",
            "Confidence Score": best_match["confidence_score"] if best_match else "N/A",
            "Matched CPE": best_match["matched_cpe"] if best_match else "N/A",
            "Title": best_match["title"] if best_match else "N/A",
            "Reasoning": best_match["reasoning"] if best_match else result.get("reasoning", "No reasoning provided")
        })

    return pd.DataFrame(formatted_results)