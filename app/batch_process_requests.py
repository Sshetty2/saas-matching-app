from query_nvd_api import query_nvd_api
from get_best_cpe_results import get_best_cpe_matches
from analyze_cpe_matches_ai import analyze_cpe_matches
from generate_nvd_query_text_ai import generate_nvd_query_text
import streamlit as st

def batch_process(software_names):
    """
    Processes software queries against the NVD API to find CPE matches, rank them,
    and analyze the best match, while updating UI progress.

    :param software_names: List of unaltered software names.
    :return: List of dictionaries with CPE match results.
    """
    results = []
    total_queries = len(software_names)
    
    # Create progress bar
    progress_bar = st.progress(0)
    
    status_text = st.empty()
    detail_text = st.empty()

    for idx, full_query in enumerate(software_names, start=1):
        progress = idx / total_queries
        progress_bar.progress(progress)
        status_text.write(f"⏳ Processing {idx}/{total_queries} applications")
        
        detail_text.write("🔍 Generating query text...")
        truncated_query = generate_nvd_query_text(full_query)
        
        detail_text.write("🌐 Querying NVD database...")
        ranked_results = get_best_cpe_matches(truncated_query, full_query)

        detail_text.write("🤖 Analyzing matches...")
        if ranked_results:
            analysis = analyze_cpe_matches(full_query, ranked_results)
        else:
            analysis = {
                "query": full_query, 
                "best_match": None, 
                "reasoning": "No relevant CPE match found."
            }

        results.append(analysis)

    progress_bar.progress(1.0)
    status_text.write("✅ Processing complete!")
    detail_text.empty()

    return results