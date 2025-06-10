import streamlit as st
import pandas as pd
import numpy as np

def prepare_slot_data(df):
    """Prepare slot data for CPD management"""
    if "supply__metrics_data__inventory" not in df.columns:
        st.error("supply__metrics_data__inventory column not found in CPD data")
        return pd.DataFrame(), pd.DataFrame()
    
    # Include BU, property, and date columns if available for supply data
    supply_cols = ["supply__id", "supply__metrics_data__inventory"]
    if "supply__dimension_dict__bu" in df.columns:
        supply_cols.append("supply__dimension_dict__bu")
    if "supply__dimension_dict__property" in df.columns:
        supply_cols.append("supply__dimension_dict__property")
    if "supply__date" in df.columns:
        supply_cols.append("supply__date")
    
    supply_data = df[supply_cols].drop_duplicates().reset_index(drop=True)
    supply_data["new_inventory"] = supply_data["supply__metrics_data__inventory"].astype(int)

    # Try to find the correct allocation ID column
    allocation_id_col = None
    possible_id_cols = ['id', 'allocation_id', 'allocation__id', 'alloc_id']
    
    for col in possible_id_cols:
        if col in df.columns:
            allocation_id_col = col
            break
    
    if allocation_id_col is None:
        id_columns = [col for col in df.columns if 'id' in col.lower()]
        if id_columns:
            allocation_id_col = id_columns[0]
        else:
            st.error("No allocation ID column found in the CPD data")
            return supply_data, pd.DataFrame()
    
    # Check if metrics_data__impressions column exists
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
            st.error("No impressions column found in the CPD data")
            return supply_data, pd.DataFrame()

    # Include BU, property, and date columns for allocation if available
    allocation_cols = [allocation_id_col, impressions_col]
    if "supply__dimension_dict__bu" in df.columns:
        allocation_cols.append("supply__dimension_dict__bu")
    if "dimension_dict__bu" in df.columns:
        allocation_cols.append("dimension_dict__bu")
    if "supply__dimension_dict__property" in df.columns:
        allocation_cols.append("supply__dimension_dict__property")
    if "supply__date" in df.columns:
        allocation_cols.append("supply__date")
    
    allocation_data = df[allocation_cols].drop_duplicates().reset_index(drop=True)
    allocation_data.rename(columns={allocation_id_col: "allocation_id", impressions_col: "metrics_data__impressions"}, inplace=True)
    allocation_data["new_impressions"] = allocation_data["metrics_data__impressions"].astype(int)

    return supply_data, allocation_data

def prepare_impression_update_data(df):
    """Prepare impression update data for CPD management"""
    if "supply__dimension_dict__rate" not in df.columns:
        st.error("supply__dimension_dict__rate column not found in CPD data")
        return pd.DataFrame()
    
    impression_cols = ["supply__id", "supply__dimension_dict__rate"]
    
    # Add cpd_impressions column if it exists
    if "supply__metrics_data__cpd_impressions" in df.columns:
        impression_cols.append("supply__metrics_data__cpd_impressions")
    
    if "supply__dimension_dict__bu" in df.columns:
        impression_cols.append("supply__dimension_dict__bu")
    if "supply__dimension_dict__property" in df.columns:
        impression_cols.append("supply__dimension_dict__property")
    if "supply__date" in df.columns:
        impression_cols.append("supply__date")
        
    impression_data = df[impression_cols].drop_duplicates().reset_index(drop=True)
    impression_data.rename(columns={"supply__dimension_dict__rate": "rate"}, inplace=True)
    impression_data["rate"] = impression_data["rate"].astype(int)
    impression_data["cpd_impressions"] = 0
    impression_data["new_rate"] = impression_data["rate"].astype(int)  # Add new_rate column
    
    # Handle cpd_impressions column if it exists
    if "supply__metrics_data__cpd_impressions" in impression_data.columns:
        impression_data["supply__metrics_data__cpd_impressions"] = impression_data["supply__metrics_data__cpd_impressions"].fillna(0).astype(int)
    
    return impression_data

def prepare_cpd_data(df):
    """Prepare CPD data for management - only works with CPD data"""
    if df is None or df.empty:
        st.error("No CPD data available for preparation")
        return
    
    required_supply_cols = ["supply__id", "supply__dimension_dict__rate"]
    missing_supply_cols = [col for col in required_supply_cols if col not in df.columns]
    
    if missing_supply_cols:
        st.error(f"Missing required CPD columns: {missing_supply_cols}")
        return
    
    # Prepare rate update data
    rate_cols = ["supply__id", "supply__dimension_dict__rate"]
    if "supply__dimension_dict__bu" in df.columns:
        rate_cols.append("supply__dimension_dict__bu")
    if "supply__dimension_dict__property" in df.columns:
        rate_cols.append("supply__dimension_dict__property")
    if "supply__date" in df.columns:
        rate_cols.append("supply__date")
    
    unique_ids = df[rate_cols].drop_duplicates().reset_index(drop=True)
    unique_ids["rate"] = unique_ids["supply__dimension_dict__rate"].astype(int)
    st.session_state.rate_update_data = unique_ids

    # Try to prepare slot data
    try:
        supply_data, allocation_data = prepare_slot_data(df)
        st.session_state.supply_slot_data = supply_data
        st.session_state.allocation_slot_data = allocation_data
    except Exception as e:
        st.error(f"Error preparing CPD slot data: {str(e)}")
        st.session_state.supply_slot_data = None
        st.session_state.allocation_slot_data = None

    # Try to prepare impression data
    try:
        st.session_state.impression_update_data = prepare_impression_update_data(df)
    except Exception as e:
        st.error(f"Error preparing CPD impression data: {str(e)}")
        st.session_state.impression_update_data = None

def initialize_cpd_session_state():
    """Initialize CPD session state variables"""
    for key in [
        "rate_update_data", "show_rate_editor",
        "supply_slot_data", "allocation_slot_data", "show_slot_editor",
        "impression_update_data", "show_impression_editor", "cpd_function"
    ]:
        if key not in st.session_state:
            if "data" in key:
                st.session_state[key] = None
            elif key == "cpd_function":
                st.session_state[key] = "Rate"
            else:
                st.session_state[key] = False

def render_rate_update_section():
    """Render rate update section for CPD data"""
    st.subheader("📊 CPD Updates")
    
    # Main dropdown for CPD Updates with sub-functions
    st.session_state.cpd_function = st.selectbox(
        "Select CPD Updates Function:",
        ["Rate", "Slot", "Impressions"],
        index=["Rate", "Slot", "Impressions"].index(st.session_state.get("cpd_function", "Rate"))
    )
    if st.session_state.cpd_function == "Rate":
        st.subheader("Update CPD Rates")

    if st.session_state.cpd_function == "Rate":
        if st.button("📝 Edit Rates", key="toggle_rate_editor"):
            st.session_state.show_rate_editor = not st.session_state.show_rate_editor

        if st.session_state.show_rate_editor and st.session_state.rate_update_data is not None:
            with st.form("rate_update_form"):
                column_config = {
                    "supply__id": st.column_config.TextColumn("Supply ID", disabled=True),
                    "supply__dimension_dict__rate": st.column_config.NumberColumn("Original Rate", disabled=True),
                    "rate": st.column_config.NumberColumn("New Rate", help="Enter new rate value")
                }
                
                if "supply__dimension_dict__bu" in st.session_state.rate_update_data.columns:
                    column_config["supply__dimension_dict__bu"] = st.column_config.TextColumn("BU", disabled=True)
                
                if "supply__dimension_dict__property" in st.session_state.rate_update_data.columns:
                    column_config["supply__dimension_dict__property"] = st.column_config.TextColumn("Property", disabled=True)
                
                if "supply__date" in st.session_state.rate_update_data.columns:
                    column_config["supply__date"] = st.column_config.TextColumn("Date", disabled=True)
                
                edited_data = st.data_editor(
                    st.session_state.rate_update_data,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="rate_data_editor",
                    column_config=column_config
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Save Rate Changes", type="primary"):
                        st.session_state.rate_update_data = edited_data
                        st.success("✅ CPD rate changes saved!")
                        st.rerun()
                with col2:
                    if st.form_submit_button("🔄 Reset to Original"):
                        edited_data["rate"] = edited_data["supply__dimension_dict__rate"].astype(int)
                        st.session_state.rate_update_data = edited_data
                        st.success("✅ Rates reset to original values!")
                        st.rerun()

        if st.session_state.rate_update_data is not None:
            changes = st.session_state.rate_update_data[
                st.session_state.rate_update_data["supply__dimension_dict__rate"] != 
                st.session_state.rate_update_data["rate"]
            ]
            if not changes.empty:
                st.info(f"📝 {len(changes)} rate(s) have been modified")
                # Download data should only include id and rate (no property or BU)
                download_data = changes[["supply__id", "rate"]].copy()
                download_data.columns = ["id", "rate"]
                download_data["rate"] = download_data["rate"].astype(int)
                
                csv = download_data.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Updated CPD Rates CSV", csv, "cpd_rate_update.csv", "text/csv")

def render_slot_update_section():
    """Render slot update section for CPD data"""
    if st.session_state.cpd_function == "Slot":
        st.subheader("Update CPD Slots")

        if st.button("📝 Edit Slots", key="toggle_slot_editor"):
            st.session_state.show_slot_editor = not st.session_state.show_slot_editor

        if st.session_state.show_slot_editor and st.session_state.supply_slot_data is not None:
            tab1, tab2 = st.tabs(["🏭 Supply Inventory", "📊 Allocation Impressions"])

            with tab1:
                if not st.session_state.supply_slot_data.empty:
                    with st.form("supply_slot_form"):
                        supply_column_config = {
                            "supply__id": st.column_config.TextColumn("Supply ID", disabled=True),
                            "supply__metrics_data__inventory": st.column_config.NumberColumn("Current Inventory", disabled=True),
                            "new_inventory": st.column_config.NumberColumn("New Inventory", help="Enter new inventory value")
                        }
                        
                        if "supply__dimension_dict__bu" in st.session_state.supply_slot_data.columns:
                            supply_column_config["supply__dimension_dict__bu"] = st.column_config.TextColumn("BU", disabled=True)
                        
                        if "supply__dimension_dict__property" in st.session_state.supply_slot_data.columns:
                            supply_column_config["supply__dimension_dict__property"] = st.column_config.TextColumn("Property", disabled=True)
                        
                        if "supply__date" in st.session_state.supply_slot_data.columns:
                            supply_column_config["supply__date"] = st.column_config.TextColumn("Date", disabled=True)
                        
                        edited_supply = st.data_editor(
                            st.session_state.supply_slot_data,
                            use_container_width=True,
                            key="supply_slot_editor",
                            column_config=supply_column_config
                        )
                        
                        if st.form_submit_button("💾 Save Supply Changes", type="primary"):
                            st.session_state.supply_slot_data = edited_supply
                            st.success("✅ CPD supply slot changes saved!")
                            st.rerun()

            with tab2:
                if not st.session_state.allocation_slot_data.empty:
                    with st.form("allocation_slot_form"):
                        allocation_column_config = {
                            "allocation_id": st.column_config.TextColumn("Allocation ID", disabled=True),
                            "metrics_data__impressions": st.column_config.NumberColumn("Current Impressions", disabled=True),
                            "new_impressions": st.column_config.NumberColumn("New Impressions", help="Enter new impressions value")
                        }
                        
                        if "supply__dimension_dict__bu" in st.session_state.allocation_slot_data.columns:
                            allocation_column_config["supply__dimension_dict__bu"] = st.column_config.TextColumn("Supply BU", disabled=True)
                        if "dimension_dict__bu" in st.session_state.allocation_slot_data.columns:
                            allocation_column_config["dimension_dict__bu"] = st.column_config.TextColumn("Allocation BU", disabled=True)
                        if "supply__dimension_dict__property" in st.session_state.allocation_slot_data.columns:
                            allocation_column_config["supply__dimension_dict__property"] = st.column_config.TextColumn("Property", disabled=True)
                        if "supply__date" in st.session_state.allocation_slot_data.columns:
                            allocation_column_config["supply__date"] = st.column_config.TextColumn("Date", disabled=True)
                        
                        edited_allocation = st.data_editor(
                            st.session_state.allocation_slot_data,
                            use_container_width=True,
                            key="allocation_slot_editor",
                            column_config=allocation_column_config
                        )
                        
                        if st.form_submit_button("💾 Save Allocation Changes", type="primary"):
                            st.session_state.allocation_slot_data = edited_allocation
                            st.success("✅ CPD allocation slot changes saved!")
                            st.rerun()

        # Show download buttons for changes
        if st.session_state.supply_slot_data is not None:
            supply_changes = st.session_state.supply_slot_data[
                st.session_state.supply_slot_data["supply__metrics_data__inventory"] != 
                st.session_state.supply_slot_data["new_inventory"]
            ]
            if not supply_changes.empty:
                # Download data should only include id and inventory (no property or BU)
                download_supply_data = supply_changes[["supply__id", "new_inventory"]].copy()
                download_supply_data.columns = ["id", "inventory"]
                download_supply_data["inventory"] = download_supply_data["inventory"].astype(int)
                
                csv = download_supply_data.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Updated CPD Supply Slots CSV", csv, "cpd_supply_slot_update.csv", "text/csv")

        if st.session_state.allocation_slot_data is not None:
            allocation_changes = st.session_state.allocation_slot_data[
                st.session_state.allocation_slot_data["metrics_data__impressions"] != 
                st.session_state.allocation_slot_data["new_impressions"]
            ]
            if not allocation_changes.empty:
                # Download data should only include id and impressions (no property or BU)
                download_allocation_data = allocation_changes[["allocation_id", "new_impressions"]].copy()
                download_allocation_data.columns = ["id", "impressions"]
                download_allocation_data["impressions"] = download_allocation_data["impressions"].astype(int)
                
                csv = download_allocation_data.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Updated CPD Allocation Slots CSV", csv, "cpd_allocation_slot_update.csv", "text/csv")

def render_impression_update_section():
    """Render impression update section for CPD data"""
    if st.session_state.cpd_function == "Impressions":
        st.subheader("Update CPD Impressions")

        if st.button("📝 Edit Impressions", key="toggle_impression_editor"):
            st.session_state.show_impression_editor = not st.session_state.show_impression_editor

        if st.session_state.show_impression_editor and st.session_state.impression_update_data is not None:
            # Ensure new_rate column exists (backward compatibility)
            if "new_rate" not in st.session_state.impression_update_data.columns:
                st.session_state.impression_update_data["new_rate"] = st.session_state.impression_update_data["rate"].astype(int)
                
            with st.form("impression_update_form"):
                impression_column_config = {
                    "supply__id": st.column_config.TextColumn("Supply ID", disabled=True),
                    "rate": st.column_config.NumberColumn("Original Rate", disabled=True),
                    "new_rate": st.column_config.NumberColumn("New Rate", help="Enter new rate value"),
                    "cpd_impressions": st.column_config.NumberColumn("CPD Impressions", help="Enter CPD impressions value")
                }
                
                # Add cpd_impressions viewer column if it exists
                if "supply__metrics_data__cpd_impressions" in st.session_state.impression_update_data.columns:
                    impression_column_config["supply__metrics_data__cpd_impressions"] = st.column_config.NumberColumn("Current CPD Impressions", disabled=True)
                
                if "supply__dimension_dict__bu" in st.session_state.impression_update_data.columns:
                    impression_column_config["supply__dimension_dict__bu"] = st.column_config.TextColumn("BU", disabled=True)
                
                if "supply__dimension_dict__property" in st.session_state.impression_update_data.columns:
                    impression_column_config["supply__dimension_dict__property"] = st.column_config.TextColumn("Property", disabled=True)
                
                if "supply__date" in st.session_state.impression_update_data.columns:
                    impression_column_config["supply__date"] = st.column_config.TextColumn("Date", disabled=True)
                
                edited_data = st.data_editor(
                    st.session_state.impression_update_data,
                    use_container_width=True,
                    key="impression_data_editor",
                    column_config=impression_column_config
                )
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.form_submit_button("💾 Save Impression Changes", type="primary"):
                        st.session_state.impression_update_data = edited_data
                        st.success("✅ CPD impressions changes saved!")
                        st.rerun()
                with col2:
                    if st.form_submit_button("🔄 Reset Impressions"):
                        edited_data["cpd_impressions"] = 0
                        st.session_state.impression_update_data = edited_data
                        st.success("✅ CPD impressions reset to zero!")
                        st.rerun()
                with col3:
                    if st.form_submit_button("🔄 Reset Rates"):
                        edited_data["new_rate"] = edited_data["rate"].astype(int)
                        st.session_state.impression_update_data = edited_data
                        st.success("✅ Rates reset to original values!")
                        st.rerun()

        if st.session_state.impression_update_data is not None:
            # Ensure new_rate column exists (backward compatibility)
            if "new_rate" not in st.session_state.impression_update_data.columns:
                st.session_state.impression_update_data["new_rate"] = st.session_state.impression_update_data["rate"].astype(int)
            
            # Check for changes in both impressions and rates
            impression_changes = st.session_state.impression_update_data[
                st.session_state.impression_update_data["cpd_impressions"] > 0
            ]
            rate_changes = st.session_state.impression_update_data[
                st.session_state.impression_update_data["rate"] != 
                st.session_state.impression_update_data["new_rate"]
            ]
            
            if not impression_changes.empty or not rate_changes.empty:
                if not impression_changes.empty:
                    st.info(f"📝 {len(impression_changes)} record(s) have CPD impressions set")
                if not rate_changes.empty:
                    st.info(f"📝 {len(rate_changes)} rate(s) have been modified")
                
                # Download data for impression changes
                if not impression_changes.empty:
                    download_impression_data = impression_changes[["supply__id", "cpd_impressions", "new_rate"]].copy()
                    download_impression_data.columns = ["id", "cpd_impressions", "rate"]
                    download_impression_data["cpd_impressions"] = download_impression_data["cpd_impressions"].astype(int)
                    download_impression_data["rate"] = download_impression_data["rate"].astype(int)
                    
                    csv = download_impression_data.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Download Updated CPD Impressions CSV", csv, "cpd_impression_update.csv", "text/csv")
                
                # Download data for rate changes
                # if not rate_changes.empty:
                #     download_rate_data = rate_changes[["supply__id", "new_rate"]].copy()
                #     download_rate_data.columns = ["id", "rate"]
                #     download_rate_data["rate"] = download_rate_data["rate"].astype(int)
                    
                #     csv = download_rate_data.to_csv(index=False).encode("utf-8")
                #     st.download_button("📥 Download Updated Rates from Impressions Tab CSV", csv, "cpd_rate_from_impressions_update.csv", "text/csv")

def render_cpd_reset_buttons():
    """Render CPD reset buttons"""
    st.subheader("🔄 CPD Updates Data Management")
    
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔄 Reset Rates", help="Reset all rate changes to original values"):
            if st.session_state.cpd_df is not None:
                rate_cols = ["supply__id", "supply__dimension_dict__rate"]
                if "supply__dimension_dict__bu" in st.session_state.cpd_df.columns:
                    rate_cols.append("supply__dimension_dict__bu")
                if "supply__dimension_dict__property" in st.session_state.cpd_df.columns:
                    rate_cols.append("supply__dimension_dict__property")
                if "supply__date" in st.session_state.cpd_df.columns:
                    rate_cols.append("supply__date")
                
                unique_ids = st.session_state.cpd_df[rate_cols].drop_duplicates().reset_index(drop=True)
                unique_ids["rate"] = unique_ids["supply__dimension_dict__rate"].astype(int)
                st.session_state.rate_update_data = unique_ids
                st.success("✅ CPD rates reset!")
                st.rerun()

    with col2:
        if st.button("🔄 Reset Slots", help="Reset all slot changes to original values"):
            if st.session_state.cpd_df is not None:
                try:
                    supply, allocation = prepare_slot_data(st.session_state.cpd_df)
                    st.session_state.supply_slot_data = supply
                    st.session_state.allocation_slot_data = allocation
                    st.success("✅ CPD slots reset!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error resetting CPD slots: {str(e)}")

    with col3:
        if st.button("🔄 Reset Impressions", help="Reset all CPD impressions to zero"):
            if st.session_state.cpd_df is not None:
                try:
                    st.session_state.impression_update_data = prepare_impression_update_data(st.session_state.cpd_df)
                    st.success("✅ CPD impressions reset!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error resetting CPD impressions: {str(e)}")

    with col4:
        if st.button("🗑️ Clear All CPD", help="Clear all CPD management data"):
            cpd_keys = [key for key in st.session_state.keys() 
                       if any(x in key for x in ["rate", "supply", "allocation", "impression", "editor"])]
            for key in cpd_keys:
                del st.session_state[key]
            st.success("✅ All CPD data cleared!")
            st.rerun()