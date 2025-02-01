import streamlit as st
from database import get_computers, get_scan_ids
from scan import run_scan
import pandas as pd


def on_computer_change():
    # Reset scan selection when computer changes
    st.session_state.selected_scan = None
    
def on_scan_change():
    # Update scan selection
    pass

# Initialize session state variables
if 'selected_computer' not in st.session_state:
    st.session_state.selected_computer = None
if 'selected_scan' not in st.session_state:
    st.session_state.selected_scan = None
if 'selected_limit' not in st.session_state:
    st.session_state.selected_limit = None

# Initialize error tracking in session state
if 'nvd_api_errors' not in st.session_state:
    st.session_state.nvd_api_errors = []

st.set_page_config(
    page_title="SaaS Installed Apps Scan",
    layout="wide",
    initial_sidebar_state="auto"
)

# Add custom CSS to enforce full height
st.markdown("""
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
""", unsafe_allow_html=True)

st.title("SaaS Installed Apps Scan")

# Select Computer Name (Handles Empty List)
computer_names = get_computers()
if not computer_names:
    st.error("No computers found in the database.")
    st.stop()

selected_computer = st.selectbox(
    "Select a Computer Name",
    options=computer_names,
    key="computer_select",
    on_change=on_computer_change
)
st.session_state.selected_computer = selected_computer

# Select Scan ID (Dynamically Updates Based on Computer)
scan_ids = get_scan_ids(selected_computer) if selected_computer else []
if not scan_ids:
    st.warning("No scans found for this computer.")
    st.stop()

selected_scan = st.selectbox(
    "Select a Scan ID",
    options=scan_ids,
    key="scan_select",
    on_change=on_scan_change
)
st.session_state.selected_scan = selected_scan

# Select Limit for Returned Applications
limit_options = [1, 5, 10, 20, 30, 50, 100, "None"]
selected_limit = st.selectbox(
    "Limit number of results",
    options=limit_options,
    index=4,
    key="limit_select"
)
st.session_state.selected_limit = selected_limit

# Run Scan Button
if st.button("Run Scan"):
    if st.session_state.selected_computer and st.session_state.selected_scan:
        with st.spinner("Running scan... please wait ⏳"):
            st.session_state.nvd_api_errors = []
            scan_results = run_scan(
                st.session_state.selected_computer,
                st.session_state.selected_scan,
                st.session_state.selected_limit
            )
        
        if scan_results is not None and not scan_results.empty:
            st.write(f"### Installed Applications for `{st.session_state.selected_computer}` (Scan ID: `{st.session_state.selected_scan}`)")
            st.dataframe(
                scan_results,
                use_container_width=True,
                height=400,
            )
        else:
            st.warning("No applications found for this scan.")

def display_nvd_api_errors():
    """Display NVD API errors in a collapsible section."""
    if st.session_state.nvd_api_errors:
        with st.expander("🚨 NVD API Errors", expanded=False):
            df = pd.DataFrame(st.session_state.nvd_api_errors)
            st.dataframe(
                df,
                use_container_width=True,
                column_order=["timestamp", "software_name", "status_code", "error_message"]
            )
            if st.button("Clear Errors"):
                st.session_state.nvd_api_errors = []
                st.rerun()

# Add this where you want to display the errors (probably near the bottom of your app)
display_nvd_api_errors()