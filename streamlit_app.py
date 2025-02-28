import asyncio

# Initialize event loop before imports to prevent
# "There is no current event loop in thread" errors,
# particularly when running in Docker
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import streamlit as st
import pandas as pd
from graph.workflow import run_workflows_parallel

# Initialize session state variables
if "software_inputs" not in st.session_state:
    st.session_state.software_inputs = [""]  # Start with one empty input
if "results" not in st.session_state:
    st.session_state.results = None

st.set_page_config(
    page_title="Software CPE Matcher", layout="wide", initial_sidebar_state="auto"
)

st.markdown(
    """
<style>
    /* Make sure the app takes full viewport height */
    [data-testid="stAppViewContainer"] {
        height: 100vh;
    }
    
    /* Removes padding/margin from the main container */
    .main .block-container {
        max-width: 100%;
    }

    /* Ensures dataframes don't overflow */
    .stDataFrame {
        width: 100%;
    }
</style>
""",
    unsafe_allow_html=True,
)


def add_input_field():
    """Add a new empty input field to the list"""
    st.session_state.software_inputs.append("")


def remove_input_field(index):
    """Remove an input field at the specified index"""
    st.session_state.software_inputs.pop(index)


def run_matching():
    """Run the CPE matching workflow for all software inputs"""
    software_list = [s for s in st.session_state.software_inputs if s.strip()]

    if not software_list:
        st.warning("Please enter at least one software name")
        return

    with st.spinner("Matching software to CPEs... please wait ⏳"):
        results = asyncio.run(run_workflows_parallel(software_list))
        st.session_state.results = results


col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.title("Software CPE Matcher")

    st.subheader("Enter Software Names")

    for i in range(len(st.session_state.software_inputs)):
        col_input, col_remove = st.columns([6, 1])
        with col_input:
            input_value = st.text_input(
                f"Software {i+1}",
                value=st.session_state.software_inputs[i],
                key=f"input_{i}",
            )
            st.session_state.software_inputs[i] = input_value

        if len(st.session_state.software_inputs) > 1:
            with col_remove:
                if st.button("✖", key=f"remove_{i}"):
                    remove_input_field(i)
                    st.rerun()

    if st.button("Add Another Software", on_click=add_input_field):
        pass

    if st.button("Match Software to CPEs", on_click=run_matching):
        pass

if st.session_state.results:
    st.subheader("CPE Matching Results")

    cpe_matches_data = []

    for result in st.session_state.results:
        if result and "cpe_match" in result:
            if result.get("error"):
                st.error(result.get("error"))
                continue
            match_data = {
                "software_alias": result.get("software_alias", "Unknown"),
                **result.get("cpe_match", {}),
            }
            cpe_matches_data.append(match_data)

    if cpe_matches_data:
        df = pd.DataFrame(cpe_matches_data)

        columns = [
            "software_alias",
            "match_type",
            "confidence_score",
            "matched_cpe",
            "reasoning",
        ]
        available_columns = [col for col in columns if col in df.columns]
        df = df[available_columns]

        st.dataframe(
            df,
            use_container_width=True,
            height=400,
        )

        with st.expander("View Full Results", expanded=False):
            st.json(st.session_state.results)
    else:
        st.warning("No CPE matches found in the results.")
