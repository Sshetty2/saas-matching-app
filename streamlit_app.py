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


def update_local_model():
    """Update the Local Model setting"""
    settings.llm.local_model = st.session_state.local_model


def update_openai_model():
    """Update the OpenAI model setting"""
    settings.llm.openai_model = st.session_state.openai_model


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

        local_model_options = [
            "deepseek-r1:14b",
            "qwen2.5:14b",
            "qwen2.5:32b",
            "llama3:8b",
            "llama3.1:8b",
            "gemma2:27b",
        ]
        local_model_default = (
            local_model_options.index(settings.llm.local_model)
            if settings.llm.local_model in local_model_options
            else 0
        )

        st.selectbox(
            "Local Model",
            options=local_model_options,
            index=local_model_default,
            key="local_model",
            on_change=update_local_model,
            help="Model used for analyzing and scoring CPE matches",
        )

    else:
        st.subheader("OpenAI Model Settings")

        openai_model_options = ["gpt-4o-mini", "gpt-4o"]
        openai_model_default = (
            openai_model_options.index(settings.llm.openai_model)
            if settings.llm.openai_model in openai_model_options
            else 0
        )

        st.selectbox(
            "OpenAI Model",
            options=openai_model_options,
            index=openai_model_default,
            key="openai_model",
            on_change=update_openai_model,
            help="OpenAI model used for analyzing and scoring CPE matches",
        )

    st.subheader("Current Configuration")
    st.write(f"Using Local Model: {settings.execution.use_local_model}")

    if settings.execution.use_local_model:
        st.write(f"Local Model: {settings.llm.local_model}")
    else:
        st.write(f"OpenAI Model: {settings.llm.openai_model}")

    st.write(f"Embedding Model: {settings.llm.embedding_model}")


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

    for result in st.session_state.results:
        if result:
            with st.container():
                st.markdown("---")

                st.markdown(
                    f"#### Software: **{result.get('software_alias', 'Unknown')}**"
                )

                if "info" in result and result["info"]:
                    st.info(result["info"])
                if "error" in result and result["error"]:
                    st.error(result["error"])

                if result.get("exact_match"):
                    exact_match = result["exact_match"]
                    st.markdown("##### Exact Match")
                    st.markdown(f"**CPE ID:** `{exact_match}`")

                if result.get("cpe_matches"):
                    cpe_matches = result["cpe_matches"]

                    if cpe_matches.get("best_match"):
                        best_match = cpe_matches["best_match"]
                        st.markdown("##### Best Match")
                        st.markdown(f"**CPE ID:** `{best_match.get('cpe_id', 'N/A')}`")
                        st.markdown(
                            f"**Reasoning:** {best_match.get('reasoning', 'N/A')}"
                        )

                    if "possible_matches" in cpe_matches and cpe_matches.get(
                        "possible_matches"
                    ):
                        with st.expander("Possible Matches", expanded=False):
                            for i, match in enumerate(cpe_matches["possible_matches"]):
                                st.markdown(f"**Match {i+1}**")
                                st.markdown(
                                    f"**CPE ID:** `{match.get('cpe_id', 'N/A')}`"
                                )
                                st.markdown(
                                    f"**Reasoning:** {match.get('reasoning', 'N/A')}"
                                )
                                if i < len(cpe_matches["possible_matches"]) - 1:
                                    st.markdown("---")

    with st.expander("View Full Results", expanded=False):
        st.json(st.session_state.results)
