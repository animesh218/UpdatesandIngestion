import streamlit as st
import pandas as pd
import numpy as np

def prepare_cpm_impression_data(df):
    """Prepare impression data for CPM management - both supply and allocation"""
    if df is None or df.empty:
        st.error("No CPM data available for impression preparation")
        return pd.DataFrame(), pd.DataFrame()
    
    # Prepare Supply Inventory Data
    supply_inventory_cols = ["supply__id"]
    if "supply__metrics_data__inventory" in df.columns:
        supply_inventory_cols.append("supply__metrics_data__inventory")
    else:
        st.error("supply__metrics_data__inventory column not found in CPM data")
        return pd.DataFrame(), pd.DataFrame()
    
    # Add optional columns for supply
    optional_supply_cols = [
        "supply__date", 
        "supply__dimension_dict__bu", 
        "supply__dimension_dict__property"
    ]
    for col in optional_supply_cols:
        if col in df.columns:
            supply_inventory_cols.append(col)
    
    supply_data = df[supply_inventory_cols].drop_duplicates().reset_index(drop=True)
    
    # Handle non-finite values in inventory column
    inventory_col = supply_data["supply__metrics_data__inventory"]
    # Replace NaN and infinite values with 0
    inventory_col = pd.to_numeric(inventory_col, errors='coerce').fillna(0)
    inventory_col = inventory_col.replace([np.inf, -np.inf], 0)
    supply_data["new_inventory"] = inventory_col.astype(int)
    
    # Add total inventory column (sum of previous and new)
    supply_data["total_inventory"] = supply_data["supply__metrics_data__inventory"] + supply_data["new_inventory"]
    
    # Prepare Allocation Impressions Data
    # Find allocation ID column
    allocation_id_col = None
    possible_id_cols = ['id', 'allocation_id', 'allocation__id', 'alloc_id']
    for col in possible_id_cols:
        if col in df.columns:
            allocation_id_col = col
            break
    
    if allocation_id_col is None:
        id_columns = [col for col in df.columns if 'id' in col.lower() and 'supply' not in col.lower()]
        if id_columns:
            allocation_id_col = id_columns[0]
        else:
            st.error("No allocation ID column found in CPM data")
            return supply_data, pd.DataFrame()
    
    # Find impressions column
    impressions_col = None
    possible_impressions_cols = ['metrics_data__impressions', 'impressions', 'allocation__metrics_data__impressions']
    for col in possible_impressions_cols:
        if col in df.columns:
            impressions_col = col
            break
    
    if impressions_col is None:
        impression_columns = [col for col in df.columns if 'impression' in col.lower()]
        if impression_columns:
            impressions_col = impression_columns[0]
        else:
            st.error("No impressions column found in CPM data")
            return supply_data, pd.DataFrame()
    
    allocation_cols = [allocation_id_col, impressions_col]
    
    # Add optional columns for allocation
    optional_allocation_cols = [
        "supply__date",
        "dimension_dict__bu",
        "supply__dimension_dict__property"
    ]
    for col in optional_allocation_cols:
        if col in df.columns:
            allocation_cols.append(col)
    
    allocation_data = df[allocation_cols].drop_duplicates().reset_index(drop=True)
    allocation_data.rename(columns={
        allocation_id_col: "allocation_id", 
        impressions_col: "metrics_data__impressions"
    }, inplace=True)
    
    # Handle non-finite values in impressions column
    impressions_col_data = allocation_data["metrics_data__impressions"]
    # Replace NaN and infinite values with 0
    impressions_col_data = pd.to_numeric(impressions_col_data, errors='coerce').fillna(0)
    impressions_col_data = impressions_col_data.replace([np.inf, -np.inf], 0)
    allocation_data["new_impressions"] = impressions_col_data.astype(int)
    
    # Add total impressions column (sum of previous and new)
    allocation_data["total_impressions"] = allocation_data["metrics_data__impressions"] + allocation_data["new_impressions"]
    
    return supply_data, allocation_data

def prepare_cpm_rate_data(df):
    """Prepare rate data for CPM management"""
    if df is None or df.empty:
        st.error("No CPM data available for rate preparation")
        return pd.DataFrame()
    
    # Required columns for rate update
    required_cols = ["supply__id", "supply__dimension_dict__rate"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.error(f"Missing required CPM rate columns: {missing_cols}")
        return pd.DataFrame()
    
    rate_cols = ["supply__id", "supply__dimension_dict__rate"]
    
    # Add optional columns for rate data
    optional_rate_cols = [
        "supply__date",
        # "supply__dimension_dict__event", 
        # "dimension_dict__bu",
        "supply__dimension_dict__property"
    ]
    for col in optional_rate_cols:
        if col in df.columns:
            rate_cols.append(col)
    
    rate_data = df[rate_cols].drop_duplicates().reset_index(drop=True)
    
    # Handle non-finite values in rate column
    rate_col_data = rate_data["supply__dimension_dict__rate"]
    # Replace NaN and infinite values with 0.0
    rate_col_data = pd.to_numeric(rate_col_data, errors='coerce').fillna(0.0)
    rate_col_data = rate_col_data.replace([np.inf, -np.inf], 0.0)
    rate_data["new_rate"] = rate_col_data.astype(float)
    
    return rate_data

def prepare_cpm_data(df):
    """Prepare CPM data for management - only works with non-CPD data"""
    if df is None or df.empty:
        st.error("No CPM data available for preparation")
        return
    
    # Prepare impression data (supply and allocation)
    try:
        supply_data, allocation_data = prepare_cpm_impression_data(df)
        st.session_state.cpm_supply_data = supply_data
        st.session_state.cpm_allocation_data = allocation_data
    except Exception as e:
        st.error(f"Error preparing CPM impression data: {str(e)}")
        st.session_state.cpm_supply_data = None
        st.session_state.cpm_allocation_data = None
    
    # Prepare rate data
    try:
        st.session_state.cpm_rate_data = prepare_cpm_rate_data(df)
    except Exception as e:
        st.error(f"Error preparing CPM rate data: {str(e)}")
        st.session_state.cpm_rate_data = None

def initialize_cpm_session_state():
    """Initialize CPM session state variables"""
    cpm_keys = [
        "cpm_supply_data", "cpm_allocation_data", "cpm_rate_data",
        "show_cpm_impression_editor", "show_cpm_rate_editor", 
        "cpm_function"
    ]
    
    for key in cpm_keys:
        if key not in st.session_state:
            if "data" in key:
                st.session_state[key] = None
            elif key == "cpm_function":
                st.session_state[key] = "Impressions"
            else:
                st.session_state[key] = False

def update_total_inventory(row):
    """Update total inventory when new_inventory changes"""
    return row["supply__metrics_data__inventory"] + row["new_inventory"]

def update_total_impressions(row):
    """Update total impressions when new_impressions changes"""
    return row["metrics_data__impressions"] + row["new_impressions"]

def render_cpm_impression_section():
    """Render CPM impression update section"""
    if st.session_state.cpm_function == "Impressions":
        st.subheader("CPM Updates - Impressions")
        
        if st.button("📝 Edit CPM Impressions", key="toggle_cpm_impression_editor"):
            st.session_state.show_cpm_impression_editor = not st.session_state.show_cpm_impression_editor
        
        if st.session_state.show_cpm_impression_editor:
            tab1, tab2 = st.tabs(["🏭 Supply Inventory", "📊 Allocation Impressions"])
            
            with tab1:
                if st.session_state.cpm_supply_data is not None and not st.session_state.cpm_supply_data.empty:
                    with st.form("cpm_supply_form"):
                        supply_column_config = {
                            "supply__id": st.column_config.TextColumn("Supply ID", disabled=True),
                            "supply__metrics_data__inventory": st.column_config.NumberColumn("Previous Inventory", disabled=True),
                            "new_inventory": st.column_config.NumberColumn("New Inventory", help="Enter new inventory value"),
                            "total_inventory": st.column_config.NumberColumn("Total Inventory", disabled=True, help="Sum of previous and new inventory")
                        }
                        
                        # Add optional columns to config
                        if "supply__date" in st.session_state.cpm_supply_data.columns:
                            supply_column_config["supply__date"] = st.column_config.TextColumn("Date", disabled=True)
                        if "supply__dimension_dict__bu" in st.session_state.cpm_supply_data.columns:
                            supply_column_config["supply__dimension_dict__bu"] = st.column_config.TextColumn("BU", disabled=True)
                        if "supply__dimension_dict__property" in st.session_state.cpm_supply_data.columns:
                            supply_column_config["supply__dimension_dict__property"] = st.column_config.TextColumn("Property", disabled=True)
                        
                        edited_supply = st.data_editor(
                            st.session_state.cpm_supply_data,
                            use_container_width=True,
                            key="cpm_supply_editor",
                            column_config=supply_column_config
                        )
                        
                        # Update total inventory when new_inventory changes
                        edited_supply["total_inventory"] = edited_supply["supply__metrics_data__inventory"] + edited_supply["new_inventory"]
                        
                        if st.form_submit_button("💾 Save Supply Changes", type="primary"):
                            st.session_state.cpm_supply_data = edited_supply
                            st.success("✅ CPM supply inventory changes saved!")
                            st.rerun()
                else:
                    st.info("No CPM supply data available for editing")
            
            with tab2:
                if st.session_state.cpm_allocation_data is not None and not st.session_state.cpm_allocation_data.empty:
                    with st.form("cpm_allocation_form"):
                        allocation_column_config = {
                            "allocation_id": st.column_config.TextColumn("Allocation ID", disabled=True),
                            "metrics_data__impressions": st.column_config.NumberColumn("Previous Impressions", disabled=True),
                            "new_impressions": st.column_config.NumberColumn("New Impressions", help="Enter new impressions value"),
                            "total_impressions": st.column_config.NumberColumn("Total Impressions", disabled=True, help="Sum of previous and new impressions")
                        }
                        
                        # Add optional columns to config
                        if "supply__date" in st.session_state.cpm_allocation_data.columns:
                            allocation_column_config["supply__date"] = st.column_config.TextColumn("Date", disabled=True)
                        if "dimension_dict__bu" in st.session_state.cpm_allocation_data.columns:
                            allocation_column_config["dimension_dict__bu"] = st.column_config.TextColumn("BU", disabled=True)
                        if "supply__dimension_dict__property" in st.session_state.cpm_allocation_data.columns:
                            allocation_column_config["supply__dimension_dict__property"] = st.column_config.TextColumn("Property", disabled=True)
                        
                        edited_allocation = st.data_editor(
                            st.session_state.cpm_allocation_data,
                            use_container_width=True,
                            key="cpm_allocation_editor",
                            column_config=allocation_column_config
                        )
                        
                        # Update total impressions when new_impressions changes
                        edited_allocation["total_impressions"] = edited_allocation["metrics_data__impressions"] + edited_allocation["new_impressions"]
                        
                        if st.form_submit_button("💾 Save Allocation Changes", type="primary"):
                            st.session_state.cpm_allocation_data = edited_allocation
                            st.success("✅ CPM allocation impressions changes saved!")
                            st.rerun()
                else:
                    st.info("No CPM allocation data available for editing")
        
        # Show download buttons for changes
        if st.session_state.cpm_supply_data is not None:
            supply_changes = st.session_state.cpm_supply_data[
                st.session_state.cpm_supply_data["supply__metrics_data__inventory"] != 
                st.session_state.cpm_supply_data["new_inventory"]
            ]
            if not supply_changes.empty:
                st.info(f"📝 {len(supply_changes)} supply inventory record(s) have been modified")
                download_supply_data = supply_changes[["supply__id", "total_inventory"]].copy()
                download_supply_data.columns = ["id", "inventory"]
                download_supply_data["inventory"] = download_supply_data["inventory"].astype(int)
                
                csv = download_supply_data.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Updated CPM Supply Inventory CSV", csv, "cpm_supply_inventory_update.csv", "text/csv")
        
        if st.session_state.cpm_allocation_data is not None:
            allocation_changes = st.session_state.cpm_allocation_data[
                st.session_state.cpm_allocation_data["metrics_data__impressions"] != 
                st.session_state.cpm_allocation_data["new_impressions"]
            ]
            if not allocation_changes.empty:
                st.info(f"📝 {len(allocation_changes)} allocation impression record(s) have been modified")
                download_allocation_data = allocation_changes[["allocation_id", "total_impressions"]].copy()
                download_allocation_data.columns = ["id", "impressions"]  # Fixed: changed from "total" to "impressions"
                download_allocation_data["impressions"] = download_allocation_data["impressions"].astype(int)
                
                csv = download_allocation_data.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Updated CPM Allocation Impressions CSV", csv, "cpm_allocation_impressions_update.csv", "text/csv")

def render_cpm_rate_section():
    """Render CPM rate update section"""
    if st.session_state.cpm_function == "Rate Update":
        st.subheader("CPM Updates - Rate Update")
        
        if st.button("📝 Edit CPM Rates", key="toggle_cpm_rate_editor"):
            st.session_state.show_cpm_rate_editor = not st.session_state.show_cpm_rate_editor
        
        if st.session_state.show_cpm_rate_editor and st.session_state.cpm_rate_data is not None:
            with st.form("cpm_rate_form"):
                rate_column_config = {
                    "supply__id": st.column_config.TextColumn("Supply ID", disabled=True),
                    "supply__dimension_dict__rate": st.column_config.NumberColumn("Previous Rate", disabled=True),
                    "new_rate": st.column_config.NumberColumn("New Rate", help="Enter new rate value")
                }
                
                # Add optional columns to config
                if "supply__date" in st.session_state.cpm_rate_data.columns:
                    rate_column_config["supply__date"] = st.column_config.TextColumn("Date", disabled=True)
                if "supply__dimension_dict__event" in st.session_state.cpm_rate_data.columns:
                    rate_column_config["supply__dimension_dict__event"] = st.column_config.TextColumn("Event", disabled=True)
                if "dimension_dict__bu" in st.session_state.cpm_rate_data.columns:
                    rate_column_config["dimension_dict__bu"] = st.column_config.TextColumn("BU", disabled=True)
                if "supply__dimension_dict__property" in st.session_state.cpm_rate_data.columns:
                    rate_column_config["supply__dimension_dict__property"] = st.column_config.TextColumn("Property", disabled=True)
                
                edited_rates = st.data_editor(
                    st.session_state.cpm_rate_data,
                    use_container_width=True,
                    key="cpm_rate_editor",
                    column_config=rate_column_config
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Save Rate Changes", type="primary"):
                        st.session_state.cpm_rate_data = edited_rates
                        st.success("✅ CPM rate changes saved!")
                        st.rerun()
                with col2:
                    if st.form_submit_button("🔄 Reset to Original"):
                        # Handle non-finite values when resetting
                        reset_rates = edited_rates["supply__dimension_dict__rate"]
                        reset_rates = pd.to_numeric(reset_rates, errors='coerce').fillna(0.0)
                        reset_rates = reset_rates.replace([np.inf, -np.inf], 0.0)
                        edited_rates["new_rate"] = reset_rates.astype(float)
                        st.session_state.cpm_rate_data = edited_rates
                        st.success("✅ CPM rates reset to original values!")
                        st.rerun()
        
        # Show download button for changes
        if st.session_state.cpm_rate_data is not None:
            rate_changes = st.session_state.cpm_rate_data[
                st.session_state.cpm_rate_data["supply__dimension_dict__rate"] != 
                st.session_state.cpm_rate_data["new_rate"]
            ]
            if not rate_changes.empty:
                st.info(f"📝 {len(rate_changes)} rate(s) have been modified")
                download_rate_data = rate_changes[["supply__id", "new_rate"]].copy()
                download_rate_data.columns = ["id", "rate"]
                
                csv = download_rate_data.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Updated CPM Rates CSV", csv, "cpm_rate_update.csv", "text/csv")

def render_cpm_update_section():
    """Render main CPM update section with function selector"""
    st.subheader("📊 CPM Updates")
    
    # Function selector dropdown
    st.session_state.cpm_function = st.selectbox(
        "Select CPM Updates Function:",
        ["Impressions", "Rate Update"],
        index=["Impressions", "Rate Update"].index(st.session_state.get("cpm_function", "Impressions"))
    )
    
    # Render appropriate section based on selection
    if st.session_state.cpm_function == "Impressions":
        render_cpm_impression_section()
    elif st.session_state.cpm_function == "Rate Update":
        render_cpm_rate_section()

def get_modified_data(df, col_old, col_new, label):
    modified = df[df[col_old] != df[col_new]].copy()
    if modified.empty:
        return None, None

    # Rename for display
    display_df = modified[["supply__id"]].copy()
    if "supply__date" in modified.columns:
        display_df["date"] = modified["supply__date"]
    if "supply__dimension_dict__property" in modified.columns:
        display_df["property"] = modified["supply__dimension_dict__property"]
    display_df[f"previous_{label}"] = modified[col_old]
    display_df[f"new_{label}"] = modified[col_new]
    display_df[f"{label}"] = (
        modified[col_old].astype(str) + " -> " + modified[col_new].astype(str)
    )

    # Prepare download - use total column for impressions/inventory
    if label == "inventory" and "total_inventory" in modified.columns:
        download_df = modified[["supply__id", "total_inventory"]].copy()
        download_df.columns = ["id", "inventory"]
    elif label == "impressions" and "total_impressions" in modified.columns:
        download_df = modified[["allocation_id", "total_impressions"]].copy()
        download_df.columns = ["id", "impressions"]
    else:
        download_df = modified[["supply__id", col_new]].copy()
        download_df.columns = ["id", label]

    return display_df, download_df

def render_download_section(df, col_old, col_new, label, file_label):
    display_df, download_df = get_modified_data(df, col_old, col_new, label)
    if display_df is not None:
        st.info(f"{len(display_df)} {label} change(s) detected")
        st.dataframe(display_df, use_container_width=True)

        csv = download_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"\U0001F4E5 Download Updated {file_label} CSV",
            data=csv,
            file_name=f"updated_{label.lower()}.csv",
            mime="text/csv"
        )

def render_cpm_export_sections():
    st.subheader("\U0001F4C2 Export Modified CPM Data")

    if (
        "cpm_supply_data" in st.session_state
        and st.session_state.cpm_supply_data is not None
    ):
        render_download_section(
            st.session_state.cpm_supply_data,
            "supply__metrics_data__inventory",
            "new_inventory",
            "inventory",
            "CPM Supply Inventory",
        )

    if (
        "cpm_allocation_data" in st.session_state
        and st.session_state.cpm_allocation_data is not None
    ):
        render_download_section(
            st.session_state.cpm_allocation_data,
            "metrics_data__impressions",
            "new_impressions",
            "impressions",
            "CPM Allocation Impressions",
        )

    if (
        "cpm_rate_data" in st.session_state
        and st.session_state.cpm_rate_data is not None
    ):
        render_download_section(
            st.session_state.cpm_rate_data,
            "supply__dimension_dict__rate",
            "new_rate",
            "rate",
            "CPM Rates",
        )

def render_cpm_reset_buttons():
    """Render CPM reset buttons"""
    st.subheader("🔄 CPM Data Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Reset Impressions", help="Reset all impression changes to original values"):
            # Check if we have the original data source
            if "non_cpd_df" in st.session_state and st.session_state.non_cpd_df is not None:
                try:
                    supply_data, allocation_data = prepare_cpm_impression_data(st.session_state.non_cpd_df)
                    st.session_state.cpm_supply_data = supply_data
                    st.session_state.cpm_allocation_data = allocation_data
                    st.success("✅ CPM impressions reset to original values!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error resetting CPM impressions: {str(e)}")
            else:
                # If we don't have original data, reset the new values to match the previous values
                if st.session_state.cpm_supply_data is not None:
                    st.session_state.cpm_supply_data["new_inventory"] = st.session_state.cpm_supply_data["supply__metrics_data__inventory"]
                    st.session_state.cpm_supply_data["total_inventory"] = st.session_state.cpm_supply_data["supply__metrics_data__inventory"] + st.session_state.cpm_supply_data["new_inventory"]
                if st.session_state.cpm_allocation_data is not None:
                    st.session_state.cpm_allocation_data["new_impressions"] = st.session_state.cpm_allocation_data["metrics_data__impressions"]
                    st.session_state.cpm_allocation_data["total_impressions"] = st.session_state.cpm_allocation_data["metrics_data__impressions"] + st.session_state.cpm_allocation_data["new_impressions"]
                st.success("✅ CPM impressions reset to original values!")
                st.rerun()
    
    with col2:
        if st.button("🔄 Reset Rates", help="Reset all rate changes to original values", key="cpm_reset_rates"):
            # Check if we have the original data source
            if "non_cpd_df" in st.session_state and st.session_state.non_cpd_df is not None:
                try:
                    st.session_state.cpm_rate_data = prepare_cpm_rate_data(st.session_state.non_cpd_df)
                    st.success("✅ CPM rates reset to original values!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error resetting CPM rates: {str(e)}")
            else:
                # If we don't have original data, reset the new values to match the previous values
                if st.session_state.cpm_rate_data is not None:
                    st.session_state.cpm_rate_data["new_rate"] = st.session_state.cpm_rate_data["supply__dimension_dict__rate"]
                st.success("✅ CPM rates reset to original values!")
                st.rerun()
    
    with col3:
        if st.button("🗑️ Clear All CPM", help="Clear all CPM management data"):
            cpm_keys = [key for key in st.session_state.keys() 
                       if any(x in key for x in ["cpm_", "show_cpm"])]
            for key in cpm_keys:
                del st.session_state[key]
            st.success("✅ All CPM data cleared!")
            st.rerun()