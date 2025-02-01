import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from query_nvd_api import query_nvd_api
import streamlit as st
load_dotenv()

model = SentenceTransformer('all-MiniLM-L6-v2')

def extract_relevant_text(cpe_data):
    """Extract relevant fields from a CPE JSON object for embedding."""
    cpe_obj = cpe_data.get('cpe', {})
    cpe_name = cpe_obj.get('cpeName', '')
    titles = " ".join([t['title'] for t in cpe_obj.get('titles', [])])
    return f"{cpe_name} {titles}".strip()

def get_embeddings(texts):
    """Generate embeddings for a list of texts."""
    return model.encode(texts)

def rank_results(query, cpe_results, top_k=3):
    """Rank CPE records based on semantic similarity to the query."""
    if not cpe_results:
        return []

    query_embedding = get_embeddings([query])
    cpe_texts = [extract_relevant_text(cpe) for cpe in cpe_results]
    cpe_embeddings = get_embeddings(cpe_texts)

    # Compute cosine similarity
    similarities = cosine_similarity(query_embedding, cpe_embeddings).flatten()

    ranked_results = sorted(zip(cpe_results, similarities), key=lambda x: x[1], reverse=True)
    
    return ranked_results[:top_k]

def get_best_cpe_matches(software_name, full_query):
    """Get top 3 best CPE matches for a given software configuration."""
    products, error_info = query_nvd_api(software_name)
    if error_info:
        st.session_state.nvd_api_errors.append(error_info)
    top_matches = rank_results(full_query, products, top_k=3)

    return [
        {
            "cpeName": match[0]['cpe']['cpeName'], 
            "title": match[0]['cpe'].get('titles', [{}])[0].get('title', 'No Title'),  
            "similarity": float(match[1])
        }
        for match in top_matches
    ]