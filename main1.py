import streamlit as st
import os
import requests
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from io import StringIO

# Import the TokenManager class
from token_manager import TokenManager

# Import CPD functions
from cpd_updates import (
    initialize_cpd_session_state, 
    render_rate_update_section, 
    render_slot_update_section, 
    render_cpd_reset_buttons,
    prepare_cpd_data,
    render_impression_update_section
)

from cpm_updates import (
    initialize_cpm_session_state,
    render_cpm_update_section,
    render_cpm_reset_buttons,
    prepare_cpm_data
)

# Load environment variables
load_dotenv()

# Load credentials
base_url = os.getenv('BASE_URL')

# Initialize TokenManager
@st.cache_resource
def get_token_manager():
    """Get cached TokenManager instance"""
    return TokenManager()

report_payload = {
    "reports": [
        {
            "view": "sdms.views.AllocationViewSet",
            "report_parameters": {
                "metrics": [],
                "annotate": [{"field": "id", "name": "allocation_id"}],
                "dimensions": [
                    "id",
                    "supply__id",
                    "supply__date",
                    "supply__dimension_dict__event",
                    "supply__dimension_dict__page",
                    "supply__dimension_dict__property",
                    "supply__dimension_dict__revenue_type",
                    "supply__dimension_dict__rate",
                    "supply__metrics_data__inventory",
                    "supply__metrics_data__cpd_impressions",
                    "dimension_dict__bu",
                    "metrics_data__impressions",
                    "metrics_data__revenue",
                    "metrics_data__calculated_impressions",
                    "is_deleted"
                ],
                "end_date_field_name": "date",
                "start_date_field_name": "date",
                "date_range": {
                    "start_date": "2025-06-01",
                    "end_date": "2025-06-01"
                }
            }
        }
    ],
    "download": "true",
    "download_format": "csv",
    "meta_in_response": True,
    "pagination": {
        "limit": 20000000,
        "offset": 0
    }
}

def initialize_session_state():
    """Initialize main session state variables"""
    if "report_generated" not in st.session_state:
        st.session_state.report_generated = False
    if "filtered_df" not in st.session_state:
        st.session_state.filtered_df = None
    if "cpd_df" not in st.session_state:
        st.session_state.cpd_df = None
    if "non_cpd_df" not in st.session_state:
        st.session_state.non_cpd_df = None
    
    # Initialize CPD session state
    initialize_cpd_session_state()

def make_report_request(start_date, end_date):
    """Make API request to generate report using TokenManager"""
    token_manager = get_token_manager()
    
    # Update report payload with dates
    report_payload["reports"][0]["report_parameters"]["date_range"]["start_date"] = start_date
    report_payload["reports"][0]["report_parameters"]["date_range"]["end_date"] = end_date

    try:
        api_endpoint = f"{base_url}/core/report/"
        
        # Use TokenManager's authenticated request method
        response = token_manager.make_authenticated_request(
            method='POST',
            url=api_endpoint,
            json=report_payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response and response.status_code == 200:
            return response.text
        elif response:
            st.error(f"Report request failed with status {response.status_code}: {response.text}")
            return None
        else:
            st.error("Failed to make authenticated request")
            return None
            
    except Exception as e:
        st.error(f"Report request failed: {e}")
        return None

def filter_report_data(csv_content, properties=None, bus=None):
    """Filter report data based on properties and business units"""
    try:
        df = pd.read_csv(StringIO(csv_content))
        if properties:
            df = df[df["supply__dimension_dict__property"].isin(properties)]
        if bus:
            df = df[df["dimension_dict__bu"].isin(bus)]
        return df
    except Exception as e:
        st.error(f"Error filtering data: {e}")
        return None

def separate_cpd_data(df):
    """Separate CPD and non-CPD data based on revenue_type column"""
    if df is None or df.empty:
        return None, None
    
    # Check if revenue_type column exists
    if "supply__dimension_dict__revenue_type" not in df.columns:
        st.warning("Revenue type column not found. All data will be treated as CPM.")
        return None, df
    
    # Convert to string and handle NaN values
    df_copy = df.copy()
    df_copy["supply__dimension_dict__revenue_type"] = df_copy["supply__dimension_dict__revenue_type"].astype(str).str.lower()
    
    # Separate CPD and non-CPD data
    cpd_df = df_copy[df_copy["supply__dimension_dict__revenue_type"].str.contains("cpd", na=False)].copy()
    non_cpd_df = df_copy[~df_copy["supply__dimension_dict__revenue_type"].str.contains("cpd", na=False)].copy()
    
    # Return None if dataframes are empty
    cpd_df = cpd_df if not cpd_df.empty else None
    non_cpd_df = non_cpd_df if not non_cpd_df.empty else None
    
    return cpd_df, non_cpd_df

def render_sidebar():
    """Render the sidebar configuration"""
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Token Management Section
        st.subheader("🔐 Token Management")
        token_manager = get_token_manager()
        
        # Show token status
        if hasattr(st.session_state, 'token_expires_at') and st.session_state.token_expires_at:
            expires_at = st.session_state.token_expires_at
            now = datetime.now()
            if expires_at > now:
                time_left = expires_at - now
                hours_left = int(time_left.seconds / 3600)
                minutes_left = int((time_left.seconds % 3600) / 60)
                st.success(f"🟢 Token expires in: {hours_left}h {minutes_left}m")
            else:
                st.warning("🟡 Token expired")
        else:
            st.info("🔵 Token status unknown")
        
        # Show refresh count
        if hasattr(st.session_state, 'refresh_count_today'):
            st.write(f"Refreshes today: {st.session_state.refresh_count_today}/10")
        
        # Manual refresh button
        if st.button("🔄 Refresh Token Manually", key="manual_refresh_btn"):
            try:
                token = token_manager.manual_refresh_token()
                if token:
                    st.success("✅ Token refreshed successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to refresh token")
            except Exception as e:
                st.error(f"❌ Refresh failed: {e}")
        
        st.divider()
        
        # Use session state for form inputs to prevent resets
        if "start_date" not in st.session_state:
            st.session_state.start_date = datetime.strptime("2025-06-01", "%Y-%m-%d").date()
        if "end_date" not in st.session_state:
            st.session_state.end_date = datetime.strptime("2025-06-01", "%Y-%m-%d").date()
        if "raw_properties" not in st.session_state:
            st.session_state.raw_properties = ""
        if "raw_bus" not in st.session_state:
            st.session_state.raw_bus = ""
        
        start_date = st.date_input("Start Date", value=st.session_state.start_date, key="start_date_input")
        end_date = st.date_input("End Date", value=st.session_state.end_date, key="end_date_input")
        raw_properties = st.text_area("Filter: Properties (comma-separated, optional)", 
                                     value=st.session_state.raw_properties, key="properties_input")
        raw_bus = st.text_area("Filter: Business Units (comma-separated, optional)", 
                              value=st.session_state.raw_bus, key="bus_input")

        # Update session state when inputs change
        st.session_state.start_date = start_date
        st.session_state.end_date = end_date
        st.session_state.raw_properties = raw_properties
        st.session_state.raw_bus = raw_bus

        # Convert input strings to lists
        property_list = [p.strip() for p in raw_properties.split(",") if p.strip()]
        bu_list = [b.strip() for b in raw_bus.split(",") if b.strip()]
        
        return start_date, end_date, property_list, bu_list

def render_data_summary():
    """Render data summary section"""
    if st.session_state.filtered_df is not None:
        total_records = len(st.session_state.filtered_df)
        cpd_count = len(st.session_state.cpd_df) if st.session_state.cpd_df is not None else 0
        non_cpd_count = len(st.session_state.non_cpd_df) if st.session_state.non_cpd_df is not None else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Total Records", total_records)
        with col2:
            st.metric("CPD Records", cpd_count)
        with col3:
            st.metric("📈 CPM Records", non_cpd_count)

def render_cpd_tab():
    """Render CPD data tab with CPD-specific functionality"""
    if st.session_state.cpd_df is not None:
        st.subheader("CPD Data Management")
        
        # Show CPD data preview
        with st.expander("📄 CPD Data Preview", expanded=False):
            st.dataframe(st.session_state.cpd_df, use_container_width=True)
            
            # Download CPD CSV
            csv = st.session_state.cpd_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CPD Data CSV", csv, "cpd_data.csv", "text/csv", key="download_cpd")
        
        st.divider()
        
        # Render CPD management sections
        render_rate_update_section()
        st.divider()
        render_slot_update_section()
        st.divider()
        render_impression_update_section()
        st.divider()
        render_cpd_reset_buttons()
        
    else:
        st.info("📭 No CPD data found in the current dataset.")
        st.write("CPD data is identified by records where the revenue_type column contains 'cpd'.")

def render_non_cpd_tab():
    """Render non-CPD data tab with CPM functionality"""
    if st.session_state.non_cpd_df is not None:
        st.subheader("📈 CPM Data Management")
        
        # Show data preview
        with st.expander("📄 CPM Data Preview", expanded=False):
            st.dataframe(st.session_state.non_cpd_df, use_container_width=True)
            
            # Download non-CPD CSV
            csv = st.session_state.non_cpd_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CPM Data CSV", csv, "non_cpd_data.csv", "text/csv", key="download_non_cpd")
        
        st.divider()
        
        # Render CPM management sections
        render_cpm_update_section()
        st.divider()
        render_cpm_reset_buttons()
    
    else:
        st.info("📭 No CPM data found in the current dataset.")

def main():
    """Main application function"""
    st.set_page_config(page_title="Allocation Report Tool", layout="wide")
    st.title("📊 Allocation Report Generator")

    # Initialize session state
    initialize_session_state()
    initialize_cpm_session_state()
    
    # Render sidebar and get configuration
    start_date, end_date, property_list, bu_list = render_sidebar()

    # Generate Report Button
    if st.button("🚀 Generate Report", key="generate_report_btn"):
        with st.spinner("Fetching and filtering report..."):
            csv_data = make_report_request(str(start_date), str(end_date))
            if csv_data:
                df = filter_report_data(csv_data, property_list, bu_list)
                if df is not None and not df.empty:
                    st.session_state.filtered_df = df
                    
                    # Separate CPD and non-CPD data
                    cpd_df, non_cpd_df = separate_cpd_data(df)
                    st.session_state.cpd_df = cpd_df
                    st.session_state.non_cpd_df = non_cpd_df
                    
                    # Prepare CPD data for management (only if CPD data exists)
                    if cpd_df is not None:
                        prepare_cpd_data(cpd_df)
                    
                    # Prepare CPM data for management (only if non-CPD data exists)
                    if non_cpd_df is not None:
                        prepare_cpm_data(non_cpd_df)
                    
                    st.session_state.report_generated = True
                    st.success("✅ Report generated successfully!")
                    
                    # Show data summary
                    render_data_summary()
                else:
                    st.error("No data found for the given filters.")
            else:
                st.error("Failed to generate report.")

    # Display results if report has been generated
    if st.session_state.report_generated:
        # Show data summary
        render_data_summary()
        
        tab_names = []
        if st.session_state.cpd_df is not None:
            tab_names.append("CPD Management")
        if st.session_state.non_cpd_df is not None:
            tab_names.append("📈 CPM Management")
        
        # Create tabs if any exist
        if tab_names:
            tabs = st.tabs(tab_names)
            tab_index = 0
            
            if st.session_state.cpd_df is not None:
                with tabs[tab_index]:
                    render_cpd_tab()
                tab_index += 1
            
            if st.session_state.non_cpd_df is not None:
                with tabs[tab_index]:
                    render_non_cpd_tab()
    
    else:
        st.info("👆 Generate a report from the Configuration panel to get started.")

if __name__ == "__main__":
    main()