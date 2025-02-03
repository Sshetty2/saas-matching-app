from queries.query_nvd_api import query_nvd_api
from agent.get_best_cpe_results import get_best_cpe_matches
from agent.analyze_cpe_matches_ai import analyze_cpe_matches
from agent.generate_nvd_query_text_ai import generate_nvd_query_text
import streamlit as st
import time
import os
from dotenv import load_dotenv

load_dotenv()

def batch_process(software_names):
    """
    Processes software queries against the NVD API to find CPE matches, rank them,
    and analyze the best match, while updating UI progress.

    :param software_names: List of unaltered software names.
    :return: List of dictionaries with CPE match results.
    """
    results = []
    total_queries = len(software_names)
    min_request_interval = int(os.getenv("MIN_REQUEST_INTERVAL"))
    
    # Create progress bar and timing displays
    
    progress_bar = st.progress(0)
    
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        status_text = st.empty()
    
    with col2:
        timer_text = st.empty()
        start_time = time.time()
    
    with col3:
        st.write(f"Min Interval: {min_request_interval}s")
    
    detail_text = st.empty()
    item_times = []

    for idx, full_query in enumerate(software_names, start=1):
        item_start_time = time.time()
        
        progress = idx / total_queries
        progress_bar.progress(progress)
        status_text.write(f"⏳ Processing {idx}/{total_queries} applications")
        
        # Update elapsed time
        elapsed = time.time() - start_time
        timer_text.write(f"⏱️ Elapsed Time: {elapsed:.1f}s")
        
        detail_text.write("🔍 Generating query text...")
        truncated_query = generate_nvd_query_text(full_query)
        
        detail_text.write(f"🌐 Querying NVD database for {truncated_query}")
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

        item_time = time.time() - item_start_time
        item_times.append({"query": full_query, "processing_time": item_time})
        results.append(analysis)

    # Final updates
    progress_bar.progress(1.0)
    status_text.write("✅ Processing complete!")
    final_time = time.time() - start_time
    timer_text.write(f"⏱️ Total Time: {final_time:.1f}s")
    detail_text.empty()

    # Display item processing times in expander
    with st.expander("📊 Individual Processing Times"):
        for item in item_times:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.write(f"**{item['query']}**:")
            with col2:
                st.write(f"{item['processing_time']:.1f}s")

    return results