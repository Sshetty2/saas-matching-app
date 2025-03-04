import asyncio

# Initialize event loop before imports to prevent
# "There is no current event loop in thread" errors,
# particularly when running in Docker
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

import streamlit as st
import pandas as pd
from graph.workflow import run_workflows_parallel
from config import settings

if "software_inputs" not in st.session_state:
    st.session_state.software_inputs = [""]
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


def update_model_setting():
    """Update the use_local_model setting based on the dropdown selection"""
    settings.execution.use_local_model = (
        st.session_state.model_selection == "Local Model"
    )


def update_local_analysis_model():
    """Update the local analysis model setting"""
    settings.llm.local_analysis_model = st.session_state.local_analysis_model


def update_local_parse_model():
    """Update the local parse model setting"""
    settings.llm.local_parse_model = st.session_state.local_parse_model


def update_openai_analysis_model():
    """Update the OpenAI analysis model setting"""
    settings.llm.openai_analysis_model = st.session_state.openai_analysis_model


def update_openai_parse_model():
    """Update the OpenAI parse model setting"""
    settings.llm.openai_parse_model = st.session_state.openai_parse_model


with st.sidebar:
    st.title("Settings")

    model_options = ["Local Model", "OpenAI Model"]
    default_index = 0 if settings.execution.use_local_model else 1

    st.selectbox(
        "Select Model",
        options=model_options,
        index=default_index,
        key="model_selection",
        on_change=update_model_setting,
        help="Choose between local models or OpenAI models",
    )

    if settings.execution.use_local_model:
        st.subheader("Local Model Settings")

        local_analysis_options = [
            "qwen2.5:14b",
            "qwen2.5:32b",
            "llama3.1:8b",
            "gemma2:27b",
        ]
        local_analysis_default = (
            local_analysis_options.index(settings.llm.local_analysis_model)
            if settings.llm.local_analysis_model in local_analysis_options
            else 0
        )

        st.selectbox(
            "Analysis Model",
            options=local_analysis_options,
            index=local_analysis_default,
            key="local_analysis_model",
            on_change=update_local_analysis_model,
            help="Model used for analyzing and scoring CPE matches",
        )

        local_parse_options = [
            "llama3.1:8b",
            "qwen2.5:14b",
            "qwen2.5:32b",
            "gemma2:27b",
        ]
        local_parse_default = (
            local_parse_options.index(settings.llm.local_parse_model)
            if settings.llm.local_parse_model in local_parse_options
            else 0
        )

        st.selectbox(
            "Parse Model",
            options=local_parse_options,
            index=local_parse_default,
            key="local_parse_model",
            on_change=update_local_parse_model,
            help="Model used for parsing software names",
        )
    else:
        st.subheader("OpenAI Model Settings")

        openai_analysis_options = ["gpt-4o-mini", "gpt-4o"]
        openai_analysis_default = (
            openai_analysis_options.index(settings.llm.openai_analysis_model)
            if settings.llm.openai_analysis_model in openai_analysis_options
            else 0
        )

        st.selectbox(
            "Analysis Model",
            options=openai_analysis_options,
            index=openai_analysis_default,
            key="openai_analysis_model",
            on_change=update_openai_analysis_model,
            help="OpenAI model used for analyzing and scoring CPE matches",
        )

        openai_parse_options = ["gpt-4o-mini", "gpt-4o"]
        openai_parse_default = (
            openai_parse_options.index(settings.llm.openai_parse_model)
            if settings.llm.openai_parse_model in openai_parse_options
            else 0
        )

        st.selectbox(
            "Parse Model",
            options=openai_parse_options,
            index=openai_parse_default,
            key="openai_parse_model",
            on_change=update_openai_parse_model,
            help="OpenAI model used for parsing software names",
        )

    st.subheader("Current Configuration")
    st.write(f"Using Local Model: {settings.execution.use_local_model}")

    if settings.execution.use_local_model:
        st.write(f"Analysis Model: {settings.llm.local_analysis_model}")
        st.write(f"Parse Model: {settings.llm.local_parse_model}")
    else:
        st.write(f"Analysis Model: {settings.llm.openai_analysis_model}")
        st.write(f"Parse Model: {settings.llm.openai_parse_model}")

    st.write(f"Embedding Model: {settings.llm.embedding_model}")
    st.write(f"Using Vector Store: {settings.execution.use_vector_store}")


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
            match_data = {
                "software_alias": result.get("software_alias", "Unknown"),
                **result.get("cpe_match", {}),
                "info": result.get("info", ""),
                "error": result.get("error", ""),
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
            "info",
            "error",
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
