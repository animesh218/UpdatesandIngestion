import streamlit as st
import pandas as pd
from datetime import datetime
from io import StringIO
import re
from rapidfuzz import fuzz
import warnings
warnings.filterwarnings('ignore')

class StreamlitMapper:
    """Handles fuzzy matching and mapping for Streamlit ingestion"""
    
    def __init__(self):
        self.user_corrections = {}
        
    def standardize_mbs_to_msb(self, text):
        """Standardize MBS to MSB format"""
        if not isinstance(text, str):
            return text
        return re.sub(r'MBS', 'MSB', re.sub(r'mbs', 'MSB', text))
    
    def get_fuzzy_suggestions(self, value, master_list, top_n=3):
        """Get fuzzy match suggestions for a value"""
        if not master_list or not isinstance(value, str):
            return []
            
        suggestions = []
        for master_item in master_list:
            similarity = fuzz.token_sort_ratio(value.lower(), str(master_item).lower())
            if similarity >= 60:
                suggestions.append((master_item, similarity))
        
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return [item for item, _ in suggestions[:top_n]]
    
    def find_best_match(self, value, master_list, threshold=90):
        """Find the best automatic match for a value"""
        if not isinstance(value, str) or not master_list:
            return value
            
        # Standardize the value
        value = self.standardize_mbs_to_msb(value)
        cleaned_value = re.sub(r'\s*\n\s*', ' ', value).strip()
        
        # Direct match
        if cleaned_value in master_list:
            return cleaned_value
        
        # Case-insensitive match
        master_lookup = {str(item).lower(): item for item in master_list}
        if cleaned_value.lower() in master_lookup:
            return master_lookup[cleaned_value.lower()]
        
        # Fuzzy match with high threshold
        best_match = None
        best_score = 0
        for master_item in master_list:
            similarity = fuzz.token_sort_ratio(cleaned_value.lower(), str(master_item).lower())
            if similarity > best_score:
                best_score = similarity
                best_match = master_item
        
        if best_score >= threshold:
            return best_match
            
        return value
    
    def validate_and_suggest(self, value, master_list, field_name):
        """Validate a value and return suggestions if not valid"""
        if not isinstance(value, str) or not master_list:
            return True, []
        
        # Try to find a match
        matched_value = self.find_best_match(value, master_list)
        
        # If matched value is in master list, it's valid
        if str(matched_value) in [str(item) for item in master_list]:
            return True, []
        
        # Get suggestions for invalid values
        suggestions = self.get_fuzzy_suggestions(value, master_list)
        return False, suggestions

def initialize_ingestion_session_state():
    """Initialize ingestion-specific session state variables"""
    if "ingestion_records" not in st.session_state:
        st.session_state.ingestion_records = []
        
    if "show_ingestion_tab" not in st.session_state:
        st.session_state.show_ingestion_tab = False
    
    if "mapping_data" not in st.session_state:
        st.session_state.mapping_data = {
            "properties": [],
            "pages": [],
            "bus": [],
            "events": []
        }
    
    if "mapping_file_uploaded" not in st.session_state:
        st.session_state.mapping_file_uploaded = False
    
    if "mapper" not in st.session_state:
        st.session_state.mapper = StreamlitMapper()
    
    if "validation_states" not in st.session_state:
        st.session_state.validation_states = {}

def load_excel_mapping(uploaded_file):
    """Load mapping data from uploaded Excel file"""
    try:
        excel_file = pd.ExcelFile(uploaded_file)
        sheet_names = excel_file.sheet_names
        
        mapping_data = {
            "properties": [],
            "pages": [],
            "bus": [],
            "events": []
        }
        
        for sheet_name in sheet_names:
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
            sheet_name_lower = sheet_name.lower().strip()
            
            # Match by sheet name
            if any(keyword in sheet_name_lower for keyword in ['property', 'properties']):
                all_values = []
                for col in df.columns:
                    values = df[col].dropna().unique().tolist()
                    all_values.extend([str(val).strip() for val in values 
                                     if str(val).strip() and str(val).strip().lower() not in ['property', 'properties']])
                mapping_data["properties"].extend(all_values)
            
            elif any(keyword in sheet_name_lower for keyword in ['page', 'pages']):
                all_values = []
                for col in df.columns:
                    values = df[col].dropna().unique().tolist()
                    all_values.extend([str(val).strip() for val in values 
                                     if str(val).strip() and str(val).strip().lower() not in ['page', 'pages']])
                mapping_data["pages"].extend(all_values)
            
            elif any(keyword in sheet_name_lower for keyword in ['business unit', 'business_unit', 'bu']):
                all_values = []
                for col in df.columns:
                    values = df[col].dropna().unique().tolist()
                    all_values.extend([str(val).strip() for val in values 
                                     if str(val).strip() and str(val).strip().lower() not in ['business unit', 'business_unit', 'bu']])
                mapping_data["bus"].extend(all_values)
            
            elif any(keyword in sheet_name_lower for keyword in ['event', 'events']):
                all_values = []
                for col in df.columns:
                    values = df[col].dropna().unique().tolist()
                    all_values.extend([str(val).strip() for val in values 
                                     if str(val).strip() and str(val).strip().lower() not in ['event', 'events']])
                mapping_data["events"].extend(all_values)
            
            else:
                # Match by column names
                columns = [col.lower().strip() for col in df.columns]
                
                for col_name, col_data in zip(df.columns, columns):
                    if any(keyword in col_data for keyword in ['property', 'properties']):
                        unique_values = df[col_name].dropna().unique().tolist()
                        mapping_data["properties"].extend([str(val).strip() for val in unique_values if str(val).strip()])
                    
                    elif any(keyword in col_data for keyword in ['page', 'pages']):
                        unique_values = df[col_name].dropna().unique().tolist()
                        mapping_data["pages"].extend([str(val).strip() for val in unique_values if str(val).strip()])
                    
                    elif any(keyword in col_data for keyword in ['bu', 'business_unit', 'business unit']):
                        unique_values = df[col_name].dropna().unique().tolist()
                        mapping_data["bus"].extend([str(val).strip() for val in unique_values if str(val).strip()])
                    
                    elif any(keyword in col_data for keyword in ['event', 'events']):
                        unique_values = df[col_name].dropna().unique().tolist()
                        mapping_data["events"].extend([str(val).strip() for val in unique_values if str(val).strip()])
        
        # Remove duplicates and sort
        for key in mapping_data:
            unique_items = []
            seen_lower = set()
            for item in mapping_data[key]:
                item_lower = item.lower()
                if item_lower not in seen_lower:
                    unique_items.append(item)
                    seen_lower.add(item_lower)
            mapping_data[key] = sorted(unique_items, key=str.lower)
        
        return mapping_data, None
        
    except Exception as e:
        return None, f"Error reading Excel file: {str(e)}"

def render_validation_feedback(field_name, value, master_list, field_key):
    """Render validation feedback and suggestions for a field"""
    if not value or not master_list:
        return value
    
    mapper = st.session_state.mapper
    is_valid, suggestions = mapper.validate_and_suggest(value, master_list, field_name)
    
    if not is_valid and suggestions:
        st.warning(f"⚠️ '{value}' might not be exact. Did you mean:")
        
        cols = st.columns(min(len(suggestions), 3))
        
        for i, suggestion in enumerate(suggestions[:3]):
            with cols[i]:
                if st.button(f"Use: {suggestion}", key=f"suggest_{field_key}_{i}"):
                    return suggestion
        
        if st.button(f"Keep original: {value}", key=f"keep_{field_key}"):
            return value
    
    elif not is_valid:
        st.info(f"ℹ️ '{value}' is not in the master list but will be accepted as custom input")
    
    return value

def render_smart_input(label, field_key, mapping_list, help_text=None):
    """Render a smart input field that allows both selection and typing"""
    if mapping_list:
        st.write(f"**{label}**")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.write("Select from list:")
            selected = st.selectbox(
                "Choose option:", 
                options=[""] + mapping_list, 
                key=f"{field_key}_dropdown",
                label_visibility="collapsed"
            )
        
        with col2:
            st.write("Or type directly:")
            typed_value = st.text_input(
                "Type value:",
                key=f"{field_key}_text",
                placeholder=f"Type {label.lower().replace(' *', '')}",
                label_visibility="collapsed"
            )
        
        if typed_value.strip():
            validated_value = render_validation_feedback(
                label.replace(' *', ''), 
                typed_value.strip(), 
                mapping_list, 
                f"{field_key}_typed"
            )
            return validated_value
        elif selected and selected.strip():
            return selected.strip()
        else:
            return ""
    else:
        return st.text_input(
            label, 
            key=f"{field_key}_text_only",
            placeholder=f"Enter {label.lower().replace(' *', '')}",
            help=help_text
        )

def render_excel_mapping_section():
    """Render Excel mapping upload section"""
    st.subheader("📋 Excel Mapping Configuration")
    st.write("Upload an Excel file containing Property, Page, Business Unit, and Event mappings")
    
    uploaded_file = st.file_uploader(
        "Choose Excel file",
        type=['xlsx', 'xls'],
        help="Upload Excel file with columns named: Property/Properties, Page/Pages, BU/Business Unit, Event/Events"
    )
    
    if uploaded_file is not None:
        if st.button("📤 Load Mapping Data", key="load_mapping_btn"):
            with st.spinner("Loading mapping data from Excel..."):
                mapping_data, error = load_excel_mapping(uploaded_file)
                
                if error:
                    st.error(f"❌ {error}")
                else:
                    st.session_state.mapping_data = mapping_data
                    st.session_state.mapping_file_uploaded = True
                    st.success("✅ Mapping data loaded successfully!")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Properties", len(mapping_data["properties"]))
                    with col2:
                        st.metric("Pages", len(mapping_data["pages"]))
                    with col3:
                        st.metric("Business Units", len(mapping_data["bus"]))
                    with col4:
                        st.metric("Events", len(mapping_data["events"]))
                    
                    st.rerun()
    
    if st.session_state.mapping_file_uploaded:
        st.success("🟢 Mapping data is loaded and ready to use")
        
        with st.expander("📄 View Loaded Mapping Data"):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.session_state.mapping_data["properties"]:
                    st.write("**Properties:**")
                    for prop in st.session_state.mapping_data["properties"][:10]:
                        st.write(f"• {prop}")
                    if len(st.session_state.mapping_data["properties"]) > 10:
                        st.write(f"... and {len(st.session_state.mapping_data['properties']) - 10} more")
                
                if st.session_state.mapping_data["pages"]:
                    st.write("**Pages:**")
                    for page in st.session_state.mapping_data["pages"][:10]:
                        st.write(f"• {page}")
                    if len(st.session_state.mapping_data["pages"]) > 10:
                        st.write(f"... and {len(st.session_state.mapping_data['pages']) - 10} more")
            
            with col2:
                if st.session_state.mapping_data["bus"]:
                    st.write("**Business Units:**")
                    for bu in st.session_state.mapping_data["bus"][:10]:
                        st.write(f"• {bu}")
                    if len(st.session_state.mapping_data["bus"]) > 10:
                        st.write(f"... and {len(st.session_state.mapping_data['bus']) - 10} more")
                
                if st.session_state.mapping_data["events"]:
                    st.write("**Events:**")
                    for event in st.session_state.mapping_data["events"][:10]:
                        st.write(f"• {event}")
                    if len(st.session_state.mapping_data["events"]) > 10:
                        st.write(f"... and {len(st.session_state.mapping_data['events']) - 10} more")
        
        if st.button("🗑️ Clear Mapping Data", key="clear_mapping_btn"):
            st.session_state.mapping_data = {
                "properties": [],
                "pages": [],
                "bus": [],
                "events": []
            }
            st.session_state.mapping_file_uploaded = False
            st.success("Mapping data cleared!")
            st.rerun()
    
    else:
        st.info("📤 Upload an Excel file to load mapping data for dropdowns, or use manual text input")

def validate_ingestion_form(date, event, bu, property_name, page, supply, allocation, impressions, rate, price_type):
    """Validate ingestion form fields"""
    errors = []
    
    if not date:
        errors.append("Date is required")
    if not event or not event.strip():
        errors.append("Event is required")
    if not bu or not bu.strip():
        errors.append("Business Unit is required")
    if not property_name or not property_name.strip():
        errors.append("Property is required")
    if not page or not page.strip():
        errors.append("Page is required")
    if supply is None or supply == "":
        errors.append("Supply is required")
    if allocation is None or allocation == "":
        errors.append("Allocation is required")
    if impressions is None or impressions == "":
        errors.append("Impressions is required")
    if rate is None or rate == "":
        errors.append("Rate is required")
    if not price_type:
        errors.append("Price Type is required")
    
    return errors

def render_batch_validation_section():
    """Render batch validation for existing records"""
    if not st.session_state.ingestion_records:
        return
    
    st.subheader("🔍 Batch Validation")
    st.write("Validate all existing records against master data")
    
    if st.button("🔍 Validate All Records", key="validate_all_btn"):
        mapper = st.session_state.mapper
        validation_results = []
        
        for i, record in enumerate(st.session_state.ingestion_records):
            record_issues = []
            
            for field, master_list in [
                ('property', st.session_state.mapping_data["properties"]),
                ('page', st.session_state.mapping_data["pages"]),
                ('bu', st.session_state.mapping_data["bus"]),
                ('event', st.session_state.mapping_data["events"])
            ]:
                if master_list and field in record:
                    is_valid, suggestions = mapper.validate_and_suggest(
                        record[field], master_list, field
                    )
                    if not is_valid:
                        record_issues.append({
                            'field': field,
                            'value': record[field],
                            'suggestions': suggestions
                        })
            
            if record_issues:
                validation_results.append({
                    'record_index': i,
                    'issues': record_issues
                })
        
        if validation_results:
            st.warning(f"⚠️ Found {len(validation_results)} records with potential issues")
            
            for result in validation_results:
                with st.expander(f"Record {result['record_index'] + 1} Issues"):
                    for issue in result['issues']:
                        st.write(f"**{issue['field'].title()}**: '{issue['value']}'")
                        if issue['suggestions']:
                            st.write("Suggestions:", ", ".join(issue['suggestions']))
                        else:
                            st.write("No close matches found")
        else:
            st.success("✅ All records validated successfully!")

def delete_records(indices):
    """Delete multiple records by indices"""
    if not indices:
        return
    
    # Sort indices in descending order to delete from end to start
    sorted_indices = sorted(indices, reverse=True)
    deleted_count = 0
    
    for index in sorted_indices:
        if 0 <= index < len(st.session_state.ingestion_records):
            del st.session_state.ingestion_records[index]
            deleted_count += 1
    
    if deleted_count > 0:
        st.success(f"Successfully deleted {deleted_count} record(s)!")
        st.rerun()

def render_records_with_delete():
    """Render records table with delete row option"""
    if not st.session_state.ingestion_records:
        return
    
    st.subheader("📋 Added Records")
    
    # Create DataFrame
    records_df = pd.DataFrame(st.session_state.ingestion_records)
    
    # Add row numbers for display
    records_df.insert(0, 'Row', range(1, len(records_df) + 1))
    
    # Display the dataframe
    st.dataframe(records_df, use_container_width=True)
    
    # Row deletion section
    st.subheader("🗑️ Delete Rows")
    
    # Create row options for deletion
    row_options = [f"Row {i+1}: {record['event']} - {record['property']}" 
                   for i, record in enumerate(st.session_state.ingestion_records)]
    
    # Multiselect for choosing rows to delete
    selected_rows = st.multiselect(
        "Select rows to delete:",
        options=row_options,
        help="You can select multiple rows to delete at once"
    )
    
    if selected_rows:
        # Extract row indices from selected options
        selected_indices = []
        for selected in selected_rows:
            row_num = int(selected.split(":")[0].replace("Row ", "")) - 1
            selected_indices.append(row_num)
        
        # Show what will be deleted
        st.write(f"**Selected {len(selected_indices)} row(s) for deletion:**")
        for idx in selected_indices:
            record = st.session_state.ingestion_records[idx]
            st.write(f"• Row {idx+1}: {record['date']} | {record['event']} | {record['property']} | {record['page']}")
        
        # Delete button with confirmation
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Delete Selected Rows", key="delete_selected_btn", use_container_width=True):
                delete_records(selected_indices)
        
        with col2:
            if st.button("❌ Cancel Selection", key="cancel_delete_btn", use_container_width=True):
                st.rerun()

def render_ingestion_tab():
    """Render the ingestion tab as a main tab"""
    st.header("📥 Data Ingestion with Smart Mapping")
    
    # Excel mapping section
    render_excel_mapping_section()
    st.divider()
    
    # Form section
    st.subheader("➕ Add New Record")
    st.write("*All fields are required")
    
    if st.session_state.mapping_file_uploaded:
        st.info("🧠 **Smart Input Mode**: Choose from dropdown OR type directly with AI-powered fuzzy matching")
    else:
        st.info("💡 **Manual Input Mode**: Upload Excel mapping file to enable smart matching")
    
    # Create form
    with st.form("ingestion_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            ing_date = st.date_input(
                "Date *", 
                value=datetime.now().date(), 
                key="form_ing_date"
            )
            
            ing_event = render_smart_input(
                "Event *", 
                "form_ing_event", 
                st.session_state.mapping_data["events"],
                "Select from dropdown or type directly"
            )
            
            ing_bu = render_smart_input(
                "Business Unit *", 
                "form_ing_bu", 
                st.session_state.mapping_data["bus"],
                "Select from dropdown or type directly"
            )
            
            ing_property = render_smart_input(
                "Property *", 
                "form_ing_property", 
                st.session_state.mapping_data["properties"],
                "Select from dropdown or type directly"
            )
            
            ing_page = render_smart_input(
                "Page *", 
                "form_ing_page", 
                st.session_state.mapping_data["pages"],
                "Select from dropdown or type directly"
            )
        
        with col2:
            ing_supply = st.number_input(
                "Supply *", 
                min_value=0, 
                key="form_ing_supply", 
                format="%d"
            )
            ing_allocation = st.number_input(
                "Allocation *", 
                min_value=0, 
                key="form_ing_allocation", 
                format="%d"
            )
            ing_impressions = st.number_input(
                "Impressions *", 
                min_value=0, 
                key="form_ing_impressions", 
                format="%d"
            )
            ing_rate = st.number_input(
                "Rate *", 
                min_value=0.0, 
                step=0.01, 
                format="%.2f", 
                key="form_ing_rate"
            )
            ing_price_type = st.selectbox(
                "Price Type *", 
                options=["", "CPD", "CPM", "CPC", "Fixed"], 
                key="form_ing_price_type",
                index=0
            )
        
        submitted = st.form_submit_button("➕ Add Record", use_container_width=True)
        
        if submitted:
            errors = validate_ingestion_form(
                ing_date, ing_event, ing_bu, ing_property, ing_page,
                ing_supply, ing_allocation, ing_impressions, ing_rate, ing_price_type
            )
            
            if errors:
                st.error("❌ Please fix the following errors:")
                for error in errors:
                    st.write(f"• {error}")
            else:
                mapper = st.session_state.mapper
                
                mapped_property = mapper.find_best_match(ing_property, st.session_state.mapping_data["properties"])
                mapped_page = mapper.find_best_match(ing_page, st.session_state.mapping_data["pages"])
                mapped_bu = mapper.find_best_match(ing_bu, st.session_state.mapping_data["bus"])
                mapped_event = mapper.find_best_match(ing_event, st.session_state.mapping_data["events"])
                
                new_record = {
                    "date": ing_date.strftime("%Y-%m-%d"),
                    "event": mapped_event,
                    "bu": mapped_bu,
                    "property": mapped_property,
                    "page": mapped_page,
                    "supply": int(ing_supply),
                    "allocation": int(ing_allocation),
                    "impressions": int(ing_impressions),
                    "rate": float(ing_rate),
                    "price_type": ing_price_type
                }
                st.session_state.ingestion_records.append(new_record)
                st.success("✅ Record added successfully with smart mapping applied!")
                st.rerun()
    
    st.divider()
    
    # Batch validation section
    render_batch_validation_section()
    st.divider()
    
    # Display records with delete functionality
    if st.session_state.ingestion_records:
        render_records_with_delete()
        
        st.divider()
        
        # Action buttons
        col_download, col_clear = st.columns(2)
        
        with col_download:
            records_df = pd.DataFrame(st.session_state.ingestion_records)
            csv_data = records_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"ingestion_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                key="download_ingestion_csv",
                use_container_width=True
            )
        
        with col_clear:
            if st.button("🗑️ Clear All Records", key="clear_records_btn", use_container_width=True):
                if st.button("⚠️ Confirm Clear All?", key="confirm_clear_all", type="secondary"):
                    st.session_state.ingestion_records = []
                    st.success("All records cleared!")
                    st.rerun()
        
        # Summary statistics
        st.subheader("📊 Summary Statistics")
        records_df = pd.DataFrame(st.session_state.ingestion_records)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Records", len(records_df))
        with col2:
            st.metric("Total Supply", f"{records_df['supply'].sum():,}")
        with col3:
            st.metric("Total Allocation", f"{records_df['allocation'].sum():,}")
        with col4:
            st.metric("Total Impressions", f"{records_df['impressions'].sum():,}")
    
    else:
        st.info("📭 No records added yet. Use the form above to add new records.")

def render_ingestion_sidebar_controls():
    """Render ingestion controls in sidebar"""
    st.subheader("📥 Ingestion Options")
    if st.button("🔄 Toggle Ingestion Tab", key="toggle_ingestion_btn"):
        st.session_state.show_ingestion_tab = not st.session_state.show_ingestion_tab
        st.rerun()
    
    ingestion_status = "🟢 Enabled" if st.session_state.show_ingestion_tab else "🔴 Disabled"
    st.write(f"Ingestion Tab Status: {ingestion_status}")

# Main execution
if __name__ == "__main__":
    st.set_page_config(page_title="Smart Data Ingestion", layout="wide")
    
    # Initialize session state
    initialize_ingestion_session_state()
    
    # Render the main ingestion interface
    render_ingestion_tab()
