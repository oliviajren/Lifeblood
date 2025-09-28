"""
Lifeblood Red Cross Australia - Donor Center Inspection Form
Databricks App with Service Principal Proxy Permission Model

PERMISSION MODEL:
- App Service Principal acts as a proxy for all database operations
- Users authenticate through the app (via Databricks Apps authentication)
- App performs all database operations on behalf of authenticated users
- No individual database permissions needed for users
- Users only need CAN_USE permission on the Databricks App itself

SECURITY FLOW:
1. User accesses the app URL
2. Databricks Apps authenticates the user
3. App retrieves user identity from request headers
4. App service principal performs database operations
5. User actions are logged with their identity for audit purposes
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os
from typing import Optional

# Import databricks.sdk with error handling for deployment environments
try:
    from databricks.sdk import WorkspaceClient
    DATABRICKS_SDK_AVAILABLE = True
except ImportError as e:
    # Don't show error immediately - wait until we try to use it
    DATABRICKS_SDK_AVAILABLE = False
    WorkspaceClient = None


@st.cache_resource
def get_workspace_client():
    """Get a WorkspaceClient instance"""
    if not DATABRICKS_SDK_AVAILABLE or WorkspaceClient is None:
        return None
    try:
        return WorkspaceClient()
    except Exception as e:
        st.warning(f"Could not initialize Databricks client: {e}")
        return None


def get_table_name() -> str:
    """Get the full table name from environment variables with fallbacks"""
    catalog = os.getenv("CATALOG_NAME", "livr")
    schema = os.getenv("SCHEMA_NAME", "lifeblood")
    table = os.getenv("TABLE_NAME", "lifeblood_app")
    
    # Handle cases where variables weren't substituted properly
    if catalog and catalog.startswith("${"):
        catalog = "livr"
    if schema and schema.startswith("${"):
        schema = "lifeblood"
    if table and table.startswith("${"):
        table = "lifeblood_app"
    
    return f"{catalog}.{schema}.{table}"


def get_current_user_email() -> Optional[str]:
    """Get the current Databricks user email - prioritize headers for Apps."""
    
    # Check if we already have the user email cached
    if 'authenticated_user_email' in st.session_state:
        return st.session_state['authenticated_user_email']
    
    # PRIORITY 1: Try to get from Databricks Apps headers (most reliable for Apps)
    try:
        if hasattr(st, 'context') and hasattr(st.context, 'headers'):
            # Try multiple header variations
            headers = st.context.headers  # type: ignore[attr-defined]
            
            # Common headers that contain user email in Databricks Apps
            header_candidates = [
                "x-forwarded-email",
                "x-forwarded-user", 
                "x-user-email",
                "x-databricks-user-email",
                "remote-user"
            ]
            
            for header in header_candidates:
                header_email = headers.get(header)
                if header_email and "@" in header_email:
                    st.session_state['authenticated_user_email'] = header_email
                    return header_email
    except Exception:
        pass
    
    # PRIORITY 2: Try environment variables (sometimes set in Apps)
    try:
        env_candidates = [
            "DATABRICKS_USER_EMAIL",
            "USER_EMAIL", 
            "REMOTE_USER"
        ]
        
        for env_var in env_candidates:
            env_email = os.getenv(env_var)
            if env_email and "@" in env_email:
                st.session_state['authenticated_user_email'] = env_email
                return env_email
    except Exception:
        pass
    
    # PRIORITY 3: Try Databricks SDK (may return service principal in Apps)
    try:
        workspace_client = get_workspace_client()
        if workspace_client is not None:
            current_user = workspace_client.current_user.me()
            if current_user and current_user.user_name and "@" in current_user.user_name:
                user_email = current_user.user_name
                # Only cache if it looks like an actual email, not a service principal ID
                st.session_state['authenticated_user_email'] = user_email
                return user_email
    except Exception:
        pass
    
    # If all methods fail, return None
    return None


def check_authentication():
    """Check if user is properly authenticated"""
    try:
        user_email = get_current_user_email()
        if user_email:
            return True, user_email
        return False, None
    except Exception as e:
        st.error(f"Authentication error: {e}")
        return False, None


def get_warehouse_connection():
    """Get connection to Databricks SQL warehouse using app context"""
    try:
        # In Databricks Apps, we should use the app's built-in authentication
        # For now, we'll return connection info that can be used with REST API calls
        
        # Get warehouse ID from environment variable
        warehouse_http_path = os.getenv("DATABRICKS_WAREHOUSE_HTTP_PATH", "/sql/1.0/warehouses/4b9b953939869799")
        warehouse_id = warehouse_http_path.split('/')[-1]
        
        # Get workspace hostname
        workspace_host = os.getenv("DATABRICKS_HOST", "https://e2-demo-field-eng.cloud.databricks.com")
        if not workspace_host.startswith("https://"):
            workspace_host = f"https://{workspace_host}"
        
        return {
            'warehouse_id': warehouse_id,
            'workspace_host': workspace_host,
            'warehouse_http_path': warehouse_http_path
        }
        
    except Exception as e:
        st.error(f"Error getting warehouse connection info: {e}")
        return None


def create_table_if_not_exists():
    """Table creation is now handled by Databricks Asset Bundle deployment"""
    # The table is created automatically when the bundle is deployed
    # This function is kept for compatibility but no longer performs table creation
    return True


def execute_sql_query(sql_query, warehouse_id=None):
    """Execute SQL query using Databricks SDK"""
    try:
        # Get warehouse ID from environment if not provided
        if warehouse_id is None:
            warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
            
            # If the warehouse ID looks like a variable that wasn't substituted, try to extract from HTTP path
            if warehouse_id and warehouse_id.startswith("${"):
                warehouse_id = None
            
            # Fallback: extract from HTTP path
            if not warehouse_id:
                warehouse_http_path = os.getenv("DATABRICKS_WAREHOUSE_HTTP_PATH", "/sql/1.0/warehouses/4b9b953939869799")
                if warehouse_http_path and not warehouse_http_path.startswith("${"):
                    warehouse_id = warehouse_http_path.split('/')[-1]
                else:
                    # Final fallback to hardcoded value
                    warehouse_id = "4b9b953939869799"
        
        # Create workspace client for this query
        workspace_client = get_workspace_client()
        response = workspace_client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=sql_query,
            wait_timeout="30s"
        )
        
        if response.status.state.value == "SUCCEEDED":
            return response.result
        else:
            st.warning(f"SQL execution failed with status: {response.status}")
            return None
            
    except Exception as e:
        # In local development without proper auth, this will fail
        # In production Databricks Apps, this should work
        if "cannot configure default credentials" in str(e):
            st.info("💡 Running in local mode - database writes require Databricks authentication")
            st.caption("To enable database writes locally, configure Databricks CLI: `databricks configure`")
        else:
            st.warning(f"Database connection error: {e}")
        return None

def load_recent_submissions_from_db():
    """Load recent submissions from the database table"""
    try:
        # Query recent submissions from the database
        table_name = get_table_name()
        query_sql = f"""
        SELECT form_date, inspector_name, user_email, submission_time,
               donation_chairs_condition, blood_collection_equipment_condition,
               monitoring_devices_condition, safety_equipment_condition,
               donor_name, donor_contact_number, donor_health_screening_completed,
               donor_consent_form_completed, notes, created_at
        FROM {table_name} 
        ORDER BY created_at DESC 
        LIMIT 10
        """
        
        result = execute_sql_query(query_sql)
        
        if result is not None and hasattr(result, 'data_array') and result.data_array:
            # Parse the results from the database
            submissions = []
            for row in result.data_array:
                if len(row) >= 14:
                    submissions.append({
                        'form_date': row[0],
                        'inspector_name': row[1],
                        'user_email': row[2],
                        'submission_time': row[3],
                        'donation_chairs_condition': row[4],
                        'blood_collection_equipment_condition': row[5],
                        'monitoring_devices_condition': row[6],
                        'safety_equipment_condition': row[7],
                        'donor_name': row[8],
                        'donor_contact_number': row[9],
                        'donor_health_screening_completed': row[10] if isinstance(row[10], bool) else str(row[10]).lower() == 'true',
                        'donor_consent_form_completed': row[11] if isinstance(row[11], bool) else str(row[11]).lower() == 'true',
                        'notes': row[12] if row[12] else "",
                        'created_at': row[13] if len(row) > 13 else row[3]
                    })
            return submissions
        else:
            # No data or connection failed
            return []
            
    except Exception as e:
        # Don't show warning for expected auth issues in development
        return []


def check_duplicate_submission(form_date, inspector_name, donation_chairs_condition, blood_collection_equipment_condition,
                              monitoring_devices_condition, safety_equipment_condition, donor_name, donor_contact_number,
                              donor_health_screening_completed, donor_consent_form_completed, notes, user_email):
    """Check if a similar submission already exists in the database"""
    try:
        # Query for existing submissions with the same key fields
        table_name = get_table_name()
        duplicate_check_sql = f"""
        SELECT id, submission_time, user_email
        FROM {table_name} 
        WHERE form_date = '{form_date}'
          AND inspector_name = '{inspector_name.replace("'", "''")}'
          AND donation_chairs_condition = '{donation_chairs_condition.replace("'", "''")}'
          AND blood_collection_equipment_condition = '{blood_collection_equipment_condition.replace("'", "''")}'
          AND monitoring_devices_condition = '{monitoring_devices_condition.replace("'", "''")}'
          AND safety_equipment_condition = '{safety_equipment_condition.replace("'", "''")}'
          AND donor_name = '{donor_name.replace("'", "''")}'
          AND donor_contact_number = '{donor_contact_number.replace("'", "''")}'
          AND donor_health_screening_completed = {str(donor_health_screening_completed).lower()}
          AND donor_consent_form_completed = {str(donor_consent_form_completed).lower()}
          AND COALESCE(notes, '') = '{notes.replace("'", "''") if notes else ""}'
        ORDER BY submission_time DESC
        LIMIT 1
        """
        
        result = execute_sql_query(duplicate_check_sql)
        
        if result is not None and hasattr(result, 'data_array') and result.data_array:
            # Found a duplicate submission
            duplicate_record = result.data_array[0]
            return True, {
                'id': duplicate_record[0],
                'submission_time': duplicate_record[1],
                'user_email': duplicate_record[2]
            }
        
        return False, None
        
    except Exception as e:
        # If duplicate check fails, allow submission to proceed
        st.warning(f"Could not check for duplicates: {e}")
        return False, None


def insert_form_data(form_date, inspector_name, donation_chairs_condition, blood_collection_equipment_condition, 
                     monitoring_devices_condition, safety_equipment_condition, donor_name, donor_contact_number,
                     donor_health_screening_completed, donor_consent_form_completed, notes, user_email):
    """Insert form data into the lifeblood_app table - DATABASE ONLY"""
    try:
        # Check for duplicate submission first
        is_duplicate, duplicate_info = check_duplicate_submission(
            form_date, inspector_name, donation_chairs_condition, blood_collection_equipment_condition,
            monitoring_devices_condition, safety_equipment_condition, donor_name, donor_contact_number,
            donor_health_screening_completed, donor_consent_form_completed, notes, user_email
        )
        
        if is_duplicate:
            st.warning("⚠️ **Duplicate Submission Detected!**")
            st.info(f"""
            **This exact form has already been submitted:**
            - **Previous Submission ID:** {duplicate_info['id']}
            - **Submitted on:** {duplicate_info['submission_time'][:19].replace('T', ' ')}
            - **Submitted by:** {duplicate_info['user_email']}
            
            If you need to make changes, please modify the form data or contact your administrator.
            """)
            return False
        
        # Generate submission time first
        submission_time = datetime.now().isoformat()
        
        # Database table information
        catalog = os.getenv("CATALOG_NAME", "livr")
        schema = os.getenv("SCHEMA_NAME", "lifeblood")
        table = os.getenv("TABLE_NAME", "lifeblood_app")
        table_info = {
            'catalog': catalog,
            'schema': schema, 
            'table': table,
            'full_table_name': get_table_name()
        }
        
        # Try to create table if it doesn't exist (handled by DAB)
        create_table_if_not_exists()
        
        # Save to database - NO LOCAL FALLBACK
        connection_info = get_warehouse_connection()
        
        if not connection_info:
            st.error("❌ Database connection unavailable. Cannot save form data.")
            st.error("Please contact your administrator - the app requires database access.")
            return False
        
        try:
            # Escape string values to prevent SQL injection
            escaped_notes = notes.replace("'", "''") if notes else ""
            escaped_inspector_name = inspector_name.replace("'", "''")
            escaped_donation_chairs = donation_chairs_condition.replace("'", "''")
            escaped_blood_collection = blood_collection_equipment_condition.replace("'", "''")
            escaped_monitoring = monitoring_devices_condition.replace("'", "''")
            escaped_safety = safety_equipment_condition.replace("'", "''")
            escaped_donor_name = donor_name.replace("'", "''")
            escaped_donor_contact = donor_contact_number.replace("'", "''")
            escaped_email = user_email.replace("'", "''")
            
            table_name = get_table_name()
            insert_sql = f"""
            INSERT INTO {table_name} 
            (form_date, inspector_name, user_email, submission_time,
             donation_chairs_condition, blood_collection_equipment_condition, 
             monitoring_devices_condition, safety_equipment_condition,
             donor_name, donor_contact_number, donor_health_screening_completed, 
             donor_consent_form_completed, notes)
            VALUES 
            ('{form_date}', '{escaped_inspector_name}', '{escaped_email}', '{submission_time}',
             '{escaped_donation_chairs}', '{escaped_blood_collection}', 
             '{escaped_monitoring}', '{escaped_safety}',
             '{escaped_donor_name}', '{escaped_donor_contact}', {str(donor_health_screening_completed).lower()}, 
             {str(donor_consent_form_completed).lower()}, '{escaped_notes}')
            """
            
            # Execute the insert using Databricks SDK
            result = execute_sql_query(insert_sql)
            
            if result is not None:
                st.success("✅ Data successfully saved to database!")
                st.info(f"🎯 Record written to Unity Catalog table: **{table_info['full_table_name']}**")
                return True
            else:
                st.error("❌ Failed to write to database. Please try again.")
                return False
                
        except Exception as e:
            st.error(f"❌ Database write failed: {e}")
            st.error("Please contact your administrator or try again.")
            return False
        
        return True
        
    except Exception as e:
        st.error(f"Error saving form data: {e}")
        return False


def get_submissions_from_database():
    """Retrieve all submissions from the database"""
    try:
        table_name = get_table_name()
        
        # Query to get all submissions ordered by submission time (newest first)
        select_sql = f"""
        SELECT 
            id,
            form_date,
            inspector_name,
            user_email,
            submission_time,
            donation_chairs_condition,
            blood_collection_equipment_condition,
            monitoring_devices_condition,
            safety_equipment_condition,
            donor_name,
            donor_contact_number,
            donor_health_screening_completed,
            donor_consent_form_completed,
            notes,
            created_at,
            last_modified_time,
            last_modified_by,
            edit_reason
        FROM {table_name}
        ORDER BY submission_time DESC
        """
        
        # Execute the query
        result = execute_sql_query(select_sql)
        
        if result and hasattr(result, 'data_array') and result.data_array:
            # Convert result to list of dictionaries
            submissions = []
            for row in result.data_array:
                submission = {
                    'id': row[0],
                    'form_date': row[1],
                    'inspector_name': row[2],
                    'user_email': row[3],
                    'submission_time': row[4],
                    'donation_chairs_condition': row[5],
                    'blood_collection_equipment_condition': row[6],
                    'monitoring_devices_condition': row[7],
                    'safety_equipment_condition': row[8],
                    'donor_name': row[9],
                    'donor_contact_number': row[10],
                    'donor_health_screening_completed': row[11],
                    'donor_consent_form_completed': row[12],
                    'notes': row[13],
                    'created_at': row[14],
                    'last_modified_time': row[15] if len(row) > 15 else None,
                    'last_modified_by': row[16] if len(row) > 16 else None,
                    'edit_reason': row[17] if len(row) > 17 else None
                }
                submissions.append(submission)
            
            return submissions
        else:
            return []
            
    except Exception as e:
        st.error(f"Error retrieving submissions from database: {e}")
        return []


def update_existing_record(record_id, form_date, inspector_name, donation_chairs_condition,
                          blood_collection_equipment_condition, monitoring_devices_condition,
                          safety_equipment_condition, donor_name, donor_contact_number,
                          donor_health_screening_completed, donor_consent_form_completed,
                          notes, edit_reason, modified_by):
    """Update an existing record in the database with audit trail"""
    try:
        table_name = get_table_name()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Escape strings to prevent SQL injection
        escaped_inspector_name = inspector_name.replace("'", "''")
        escaped_donor_name = donor_name.replace("'", "''")
        escaped_donor_contact = donor_contact_number.replace("'", "''")
        escaped_notes = notes.replace("'", "''") if notes else ""
        escaped_edit_reason = edit_reason.replace("'", "''")
        escaped_modified_by = modified_by.replace("'", "''")
        
        # Prepare the UPDATE statement
        update_sql = f"""
        UPDATE {table_name} 
        SET 
            form_date = '{form_date}',
            inspector_name = '{escaped_inspector_name}',
            donation_chairs_condition = '{donation_chairs_condition}',
            blood_collection_equipment_condition = '{blood_collection_equipment_condition}',
            monitoring_devices_condition = '{monitoring_devices_condition}',
            safety_equipment_condition = '{safety_equipment_condition}',
            donor_name = '{escaped_donor_name}',
            donor_contact_number = '{escaped_donor_contact}',
            donor_health_screening_completed = {str(donor_health_screening_completed).lower()},
            donor_consent_form_completed = {str(donor_consent_form_completed).lower()},
            notes = '{escaped_notes}',
            last_modified_time = '{current_time}',
            last_modified_by = '{escaped_modified_by}',
            edit_reason = '{escaped_edit_reason}'
        WHERE id = {record_id}
        """
        
        # Execute the query
        result = execute_sql_query(update_sql)
        
        if result is not None:
            # Log the edit for audit purposes
            st.info(f"📝 Record ID {record_id} updated by {modified_by} at {current_time}")
            st.info(f"📋 Edit reason: {edit_reason}")
            return True
        else:
            return False
            
    except Exception as e:
        st.error(f"Error updating record: {e}")
        return False


def view_all_submissions():
    """Display all submissions in exact raw table format"""
    # st.caption(f"Showing exact content from `{get_table_name()}` table (read-only)")
    
    # Get submissions from database
    db_submissions = get_submissions_from_database()
    
    if db_submissions:
        st.info(f"📊 Found {len(db_submissions)} records in database table")
        
        # Display exact raw table content - all columns as they appear in the database
        raw_data = []
        for submission in db_submissions:
            raw_data.append({
                'id': submission['id'],
                'form_date': submission['form_date'],
                'inspector_name': submission['inspector_name'],
                'user_email': submission['user_email'],
                'submission_time': submission['submission_time'],
                'donation_chairs_condition': submission['donation_chairs_condition'],
                'blood_collection_equipment_condition': submission['blood_collection_equipment_condition'],
                'monitoring_devices_condition': submission['monitoring_devices_condition'],
                'safety_equipment_condition': submission['safety_equipment_condition'],
                'donor_name': submission['donor_name'],
                'donor_contact_number': submission['donor_contact_number'],
                'donor_health_screening_completed': 'Yes' if submission['donor_health_screening_completed'] else 'No',
                'donor_consent_form_completed': 'Yes' if submission['donor_consent_form_completed'] else 'No',
                'notes': submission['notes'],
                'created_at': submission['created_at'],
                'last_modified_time': submission['last_modified_time'],
                'last_modified_by': submission['last_modified_by'],
                'edit_reason': submission['edit_reason']
            })
        
        # Convert to DataFrame and display with exact column names from database
        df_raw = pd.DataFrame(raw_data)
        
        st.dataframe(
            df_raw,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "form_date": st.column_config.DateColumn("Form Date", width="medium"),
                "inspector_name": st.column_config.TextColumn("Inspector Name", width="medium"),
                "user_email": st.column_config.TextColumn("User Email", width="medium"),
                "submission_time": st.column_config.DatetimeColumn("Submission Time", width="medium"),
                "donation_chairs_condition": st.column_config.TextColumn("Donation Chairs", width="medium"),
                "blood_collection_equipment_condition": st.column_config.TextColumn("Blood Collection Equip", width="medium"),
                "monitoring_devices_condition": st.column_config.TextColumn("Monitoring Devices", width="medium"),
                "safety_equipment_condition": st.column_config.TextColumn("Safety Equipment", width="medium"),
                "donor_name": st.column_config.TextColumn("Donor Name", width="medium"),
                "donor_contact_number": st.column_config.TextColumn("Donor Contact", width="medium"),
                "donor_health_screening_completed": st.column_config.TextColumn("Health Screening", width="small"),
                "donor_consent_form_completed": st.column_config.TextColumn("Consent Form", width="small"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                "created_at": st.column_config.DatetimeColumn("Created At", width="medium"),
                "last_modified_time": st.column_config.DatetimeColumn("Last Modified", width="medium"),
                "last_modified_by": st.column_config.TextColumn("Modified By", width="medium"),
                "edit_reason": st.column_config.TextColumn("Edit Reason", width="large")
            }
        )
        
        # Show table info
        st.markdown("**Table Information:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(db_submissions))
        with col2:
            modified_records = sum(1 for s in db_submissions if s.get('last_modified_time'))
            st.metric("Modified Records", modified_records)
        with col3:
            unique_users = len(set(s['user_email'] for s in db_submissions))
            st.metric("Unique Users", unique_users)
    else:
        st.info("📝 No submissions found.")
        st.caption(f"Data will be stored in `{get_table_name()}` table")


def show_record_comparison(original_record, updated_record):
    """Display before and after comparison of edited record"""
    st.markdown("### 📊 Record Changes Comparison")
    st.info("Below is a detailed comparison showing what changed in this record.")
    
    # Create comparison data
    comparison_data = []
    
    # Define fields to compare with user-friendly names
    fields_to_compare = {
        'form_date': 'Form Date',
        'inspector_name': 'Inspector Name',
        'donation_chairs_condition': 'Donation Chairs Condition',
        'blood_collection_equipment_condition': 'Blood Collection Equipment',
        'monitoring_devices_condition': 'Monitoring Devices Condition',
        'safety_equipment_condition': 'Safety Equipment Condition',
        'donor_name': 'Donor Name',
        'donor_contact_number': 'Donor Contact Number',
        'donor_health_screening_completed': 'Health Screening Completed',
        'donor_consent_form_completed': 'Consent Form Completed',
        'notes': 'Notes'
    }
    
    # Compare each field
    for field_key, field_name in fields_to_compare.items():
        original_value = original_record.get(field_key, '')
        updated_value = updated_record.get(field_key, '')
        
        # Handle None values
        if original_value is None:
            original_value = ''
        if updated_value is None:
            updated_value = ''
        
        # Convert boolean values to readable format
        # Handle both actual booleans and string representations
        if isinstance(original_value, bool):
            original_value = 'Yes' if original_value else 'No'
        elif str(original_value).lower() in ['true', 'false']:
            original_value = 'Yes' if str(original_value).lower() == 'true' else 'No'
        
        if isinstance(updated_value, bool):
            updated_value = 'Yes' if updated_value else 'No'
        elif str(updated_value).lower() in ['true', 'false']:
            updated_value = 'Yes' if str(updated_value).lower() == 'true' else 'No'
        
        # Convert to string for comparison
        original_str = str(original_value)
        updated_str = str(updated_value)
        
        # Determine if changed
        changed = original_str != updated_str
        change_indicator = "🔄 CHANGED" if changed else "✅ No Change"
        
        comparison_data.append({
            'Field': field_name,
            'Before': original_str,
            'After': updated_str,
            'Status': change_indicator
        })
    
    # Display comparison table
    df_comparison = pd.DataFrame(comparison_data)
    
    st.dataframe(
        df_comparison,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Field": st.column_config.TextColumn("Field Name", width="medium"),
            "Before": st.column_config.TextColumn("Before (Original)", width="large"),
            "After": st.column_config.TextColumn("After (Updated)", width="large"),
            "Status": st.column_config.TextColumn("Change Status", width="medium")
        }
    )
    
    # Show audit information
    st.markdown("### 📋 Audit Information")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Record ID", updated_record['id'])
    with col2:
        st.metric("Modified By", updated_record['last_modified_by'])
    with col3:
        st.metric("Modified At", updated_record['last_modified_time'])
    
    # Show edit reason
    if updated_record.get('edit_reason'):
        st.markdown("**Edit Reason:**")
        st.info(updated_record['edit_reason'])
    
    # Show summary of changes
    changed_fields = [item for item in comparison_data if "CHANGED" in item['Status']]
    if changed_fields:
        st.markdown(f"**Summary:** {len(changed_fields)} field(s) were modified in this update.")
        with st.expander("📝 Changed Fields Summary", expanded=False):
            for field in changed_fields:
                st.write(f"• **{field['Field']}**: '{field['Before']}' → '{field['After']}'")
    else:
        st.warning("⚠️ No fields were actually changed in this update.")


def edit_existing_record(user_email: str):
    """Interface for editing existing inspection records"""
    # Get all submissions for selection
    db_submissions = get_submissions_from_database()
    
    if not db_submissions:
        st.info("📝 No existing submissions found to edit.")
        return
    
    # Create selection options
    selection_options = []
    for submission in db_submissions:
        option_text = f"ID {submission['id']} - {submission['form_date']} - {submission['inspector_name']} - {submission['donor_name']}"
        selection_options.append((option_text, submission))
    
    # Record selection
    st.subheader("1️⃣ Select Record to Edit")
    selected_option = st.selectbox(
        "Choose an inspection record to edit:",
        options=[opt[0] for opt in selection_options],
        help="Records are shown as: ID - Date - Inspector - Donor Name"
    )
    
    if selected_option:
        # Find the selected submission
        selected_submission = next(opt[1] for opt in selection_options if opt[0] == selected_option)
        
        st.success(f"✅ Selected Record ID: {selected_submission['id']}")
        
        # Show original submission details
        with st.expander("📋 Original Submission Details", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Original Submitted By:** {selected_submission['user_email']}")
                st.write(f"**Original Submission Time:** {selected_submission['submission_time']}")
                st.write(f"**Form Date:** {selected_submission['form_date']}")
                st.write(f"**Inspector:** {selected_submission['inspector_name']}")
            with col2:
                st.write(f"**Donor Name:** {selected_submission['donor_name']}")
                st.write(f"**Donor Contact:** {selected_submission['donor_contact_number']}")
                st.write(f"**Health Screening:** {'✅ Complete' if selected_submission['donor_health_screening_completed'] else '❌ Incomplete'}")
                st.write(f"**Consent Form:** {'✅ Complete' if selected_submission['donor_consent_form_completed'] else '❌ Incomplete'}")
        
        # Edit form
        st.subheader("2️⃣ Edit Record")
        st.warning("⚠️ **Important:** You are editing an existing record. Changes will be tracked for audit purposes.")
        
        # Create the edit form with pre-populated values - matching original form layout
        with st.form("edit_inspection_form"):
            st.subheader("🏥 Lifeblood Donor Center Inspection & Compliance Form")
            
            # Top section: Date and Inspector
            st.markdown("### 📅 Form Information")
            col_date, col_inspector = st.columns(2)
            
            with col_date:
                form_date = st.date_input(
                    "Inspection Date *",
                    value=pd.to_datetime(selected_submission['form_date']).date(),
                    help="Select the date for this inspection"
                )
            
            with col_inspector:
                inspector_name = st.text_input(
                    "Inspector Name *",
                    value=selected_submission['inspector_name'],
                    placeholder="Enter inspector's full name",
                    help="Name of the person conducting this inspection"
                )
            
            st.markdown("---")
            
            # Two-column layout: Equipment (Left) and Donor Compliance (Right)
            col_equipment, col_donor = st.columns(2)
            
            # LEFT COLUMN: Equipment Status Check
            with col_equipment:
                st.markdown("### 🔧 Equipment Status Check")
                st.markdown("*Check the condition of each equipment type*")
                
                condition_options = ["Good", "Needs Attention", "Out of Service"]
                
                # Find current index for each condition
                chairs_index = condition_options.index(selected_submission['donation_chairs_condition']) if selected_submission['donation_chairs_condition'] in condition_options else 0
                blood_index = condition_options.index(selected_submission['blood_collection_equipment_condition']) if selected_submission['blood_collection_equipment_condition'] in condition_options else 0
                monitoring_index = condition_options.index(selected_submission['monitoring_devices_condition']) if selected_submission['monitoring_devices_condition'] in condition_options else 0
                safety_index = condition_options.index(selected_submission['safety_equipment_condition']) if selected_submission['safety_equipment_condition'] in condition_options else 0
                
                donation_chairs_condition = st.selectbox(
                    "Donation Chairs *",
                    options=condition_options,
                    index=chairs_index,
                    help="Condition of donor chairs and seating equipment"
                )
                
                blood_collection_equipment_condition = st.selectbox(
                    "Blood Collection Equipment *",
                    options=condition_options,
                    index=blood_index,
                    help="Condition of collection bags, tubing, needles, and related equipment"
                )
                
                monitoring_devices_condition = st.selectbox(
                    "Monitoring Devices *",
                    options=condition_options,
                    index=monitoring_index,
                    help="Condition of blood pressure monitors, scales, and other monitoring equipment"
                )
                
                safety_equipment_condition = st.selectbox(
                    "Safety Equipment *",
                    options=condition_options,
                    index=safety_index,
                    help="Condition of emergency equipment, first aid supplies, and safety devices"
                )
            
            # RIGHT COLUMN: Donor Compliance Check
            with col_donor:
                st.markdown("### 🩸 Donor Compliance Check")
                st.markdown("*Verify donor information and compliance*")
                
                donor_name = st.text_input(
                    "Donor Name *",
                    value=selected_submission['donor_name'],
                    placeholder="Enter donor's full name",
                    help="Full name of the donor being processed"
                )
                
                donor_contact_number = st.text_input(
                    "Contact Number *",
                    value=selected_submission['donor_contact_number'],
                    placeholder="Enter donor's contact number (numbers only)",
                    help="Donor's primary contact number (numbers only, no spaces or special characters)"
                )
                
                # Validate that contact number contains only digits
                if donor_contact_number and not donor_contact_number.isdigit():
                    st.error("⚠️ Contact number must contain only numbers (0-9)")
                
                # Convert boolean values to Yes/No for dropdown
                health_screening_value = "Yes" if selected_submission['donor_health_screening_completed'] else "No"
                consent_form_value = "Yes" if selected_submission['donor_consent_form_completed'] else "No"
                
                donor_health_screening_completed = st.selectbox(
                    "Health Screening Completed *",
                    options=["Yes", "No"],
                    index=0 if health_screening_value == "Yes" else 1,
                    help="Has the donor health screening been completed?"
                )
                
                donor_consent_form_completed = st.selectbox(
                    "Consent Form Completed *",
                    options=["Yes", "No"],
                    index=0 if consent_form_value == "Yes" else 1,
                    help="Has the donor consent form been completed and signed?"
                )
            
            # Bottom section: Notes
            st.markdown("---")
            st.markdown("### 📝 Additional Notes")
            notes = st.text_area(
                "Additional observations or notes (optional):",
                value=selected_submission['notes'] or "",
                placeholder="Enter any additional notes, observations, or issues that need attention...",
                height=100
            )
            
            # Edit reason (for audit trail)
            st.markdown("---")
            st.markdown("### 📋 Edit Information")
            edit_reason = st.text_area(
                "Reason for Edit *",
                placeholder="Please explain why this record is being modified (required for audit trail)",
                help="This information will be stored for audit purposes",
                height=80
            )
            
            # Submit button
            submitted = st.form_submit_button("💾 Update Record", type="primary")
            
            if submitted:
                # Validation
                errors = []
                
                if not inspector_name.strip():
                    errors.append("Inspector Name is required")
                
                if not donation_chairs_condition:
                    errors.append("Donation Chairs condition must be selected")
                if not blood_collection_equipment_condition:
                    errors.append("Blood Collection Equipment condition must be selected")
                if not monitoring_devices_condition:
                    errors.append("Monitoring Devices condition must be selected")
                if not safety_equipment_condition:
                    errors.append("Safety Equipment condition must be selected")
                
                if not donor_name.strip():
                    errors.append("Donor Name is required")
                if not donor_contact_number.strip():
                    errors.append("Donor Contact Number is required")
                elif not donor_contact_number.isdigit():
                    errors.append("Donor Contact Number must contain only numbers")
                elif len(donor_contact_number) < 8 or len(donor_contact_number) > 15:
                    errors.append("Donor Contact Number must be between 8 and 15 digits")
                
                if not edit_reason.strip():
                    errors.append("Reason for Edit is required")
                
                if errors:
                    st.error("❌ Please fix the following errors:")
                    for error in errors:
                        st.error(f"• {error}")
                else:
                    # Convert Yes/No back to boolean for database storage
                    health_screening_bool = (donor_health_screening_completed == "Yes")
                    consent_form_bool = (donor_consent_form_completed == "Yes")
                    
                    # Update the record
                    success = update_existing_record(
                        record_id=selected_submission['id'],
                        form_date=form_date,
                        inspector_name=inspector_name,
                        donation_chairs_condition=donation_chairs_condition,
                        blood_collection_equipment_condition=blood_collection_equipment_condition,
                        monitoring_devices_condition=monitoring_devices_condition,
                        safety_equipment_condition=safety_equipment_condition,
                        donor_name=donor_name,
                        donor_contact_number=donor_contact_number,
                        donor_health_screening_completed=health_screening_bool,
                        donor_consent_form_completed=consent_form_bool,
                        notes=notes,
                        edit_reason=edit_reason,
                        modified_by=user_email
                    )
                    
                    if success:
                        st.success("✅ Record updated successfully!")
                        
                        # Show before and after comparison
                        show_record_comparison(
                            original_record=selected_submission,
                            updated_record={
                                'id': selected_submission['id'],
                                'form_date': str(form_date),
                                'inspector_name': inspector_name,
                                'donation_chairs_condition': donation_chairs_condition,
                                'blood_collection_equipment_condition': blood_collection_equipment_condition,
                                'monitoring_devices_condition': monitoring_devices_condition,
                                'safety_equipment_condition': safety_equipment_condition,
                                'donor_name': donor_name,
                                'donor_contact_number': donor_contact_number,
                                'donor_health_screening_completed': health_screening_bool,
                                'donor_consent_form_completed': consent_form_bool,
                                'notes': notes,
                                'edit_reason': edit_reason,
                                'last_modified_by': user_email,
                                'last_modified_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                        )
                        
                        # Add refresh info after showing comparison
                        st.markdown("---")
                        st.info("💡 To edit another record, please refresh the page or change the mode selection above.")
                    else:
                        st.error("❌ Failed to update record. Please try again.")


def main():
    st.set_page_config(
        page_title="Lifeblood Red Cross Australia - Donor Center Check Form",
        page_icon="🩸",
        layout="wide"
    )
    
    # Check authentication first
    is_authenticated, user_email = check_authentication()
    
    if not is_authenticated or not user_email:
        st.error("❌ Authentication required. Please ensure you're logged into Databricks.")
        st.info("🔗 If you're seeing this message, please:")
        st.markdown("""
        1. Make sure you're logged into your Databricks workspace
        2. Try refreshing the page
        3. If running locally, ensure Databricks CLI is configured: `databricks configure`
        4. Contact your administrator if the issue persists
        """)
        return
    
    # SIDEBAR - Static Elements
    with st.sidebar:
        # 1. Title
        st.title("🩸 Lifeblood Red Cross Australia")
        st.markdown("**Donor Center Equipment & Compliance Check Form**")
        st.markdown("---")
        
        # 2. Form Guidance
        # Dropdown for detailed instructions
        st.subheader("**Form Guidance**")
        with st.expander("**📋 How to Complete This Inspection Form**", expanded=False):
            st.markdown("""
            **Requirements:**
            - Fill in the form for all **required fields**. 
            - Any observations or issues can be added in the **Additional Notes** field.
          
            **Reminders:** 
            - All submissions are recorded with your user email and time of submission in the database.
            - If you need to submit on behalf of someone else, please override the user email in the **Advanced: Override User Email (if needed)** field.
            """)
        

        
        # 3. Mode Selection
        st.subheader("**Select Mode**")
        mode = st.radio(
            "Choose your action:",
            ["📝 Submit New Inspection", "✏️ Edit Existing Inspection", "📊 View All Submissions"],
            label_visibility="collapsed"
        )
        st.markdown("---")
        
        # 4. Login Details
        st.subheader("**Login Details**")
        st.success(f"👋 Welcome **{user_email}**!")
        st.caption("  ✅ Authenticated with Databricks")
        
        # Allow user to override email if needed (but make it less prominent)
        with st.expander("🔧 Advanced: Override User Email (if needed)", expanded=False):
            st.caption("⚠️ Only change this if you need to submit on behalf of someone else")
            custom_email = st.text_input(
                "Custom Email Address",
                value=user_email,
                help="This will override the detected user email for form submissions"
            )
            if custom_email and custom_email != user_email:
                user_email = custom_email
                st.warning(f"📝 Form will be submitted as: **{user_email}** (overridden)")
            else:
                st.info(f"📝 Form will be submitted as: **{user_email}**")
        
        st.markdown("---")
        

    
    # MAIN CONTENT AREA - Dynamic Content Based on Mode Selection
    if mode == "✏️ Edit Existing Inspection":
        st.header("✏️ Edit Existing Inspection")
        st.markdown("---")
        edit_existing_record(user_email)
        return
    elif mode == "📊 View All Submissions":
        st.header("📊 View All Submissions")
        st.markdown("---")
        view_all_submissions()
        return
    
    # Continue with new submission form (default mode)
    st.header("📝 Submit New Inspection")
    st.markdown("---")
    
    # Create the PowerApps-style form
    with st.form("lifeblood_inspection_form"):
        st.subheader("🏥 Lifeblood Donor Center Inspection & Compliance Form")
        
        # Top section: Date and Inspector
        st.markdown("### 📅 Form Information")
        col_date, col_inspector = st.columns(2)
        
        with col_date:
            form_date = st.date_input(
                "Inspection Date *",
                value=datetime.now().date(),
                help="Select the date for this inspection"
            )
        
        with col_inspector:
            inspector_name = st.text_input(
                "Inspector Name *",
                placeholder="Enter inspector's full name",
                help="Name of the person conducting this inspection"
            )
        
        st.markdown("---")
        
        # Two-column layout: Equipment (Left) and Donor Compliance (Right)
        col_equipment, col_donor = st.columns(2)
        
        # LEFT COLUMN: Equipment Status Check
        with col_equipment:
            st.markdown("### 🔧 Equipment Status Check")
            st.markdown("*Check the condition of each equipment type*")
            
            condition_options = ["Good", "Needs Attention", "Out of Service"]
            
            donation_chairs_condition = st.selectbox(
                "Donation Chairs *",
                options=[""] + condition_options,
                help="Condition of donor chairs and seating equipment"
            )
            
            blood_collection_equipment_condition = st.selectbox(
                "Blood Collection Equipment *",
                options=[""] + condition_options,
                help="Condition of collection bags, tubing, needles, and related equipment"
            )
            
            monitoring_devices_condition = st.selectbox(
                "Monitoring Devices *",
                options=[""] + condition_options,
                help="Condition of blood pressure monitors, scales, and other monitoring equipment"
            )
            
            safety_equipment_condition = st.selectbox(
                "Safety Equipment *",
                options=[""] + condition_options,
                help="Condition of emergency equipment, first aid supplies, and safety devices"
            )
        
        # RIGHT COLUMN: Donor Compliance Check
        with col_donor:
            st.markdown("### 🩸 Donor Compliance Check")
            st.markdown("*Verify donor information and compliance*")
            
            donor_name = st.text_input(
                "Donor Name *",
                placeholder="Enter donor's full name",
                help="Full name of the donor being processed"
            )
            
            donor_contact_number = st.text_input(
                "Contact Number *",
                placeholder="Enter donor's contact number (numbers only)",
                help="Donor's primary contact number (numbers only, no spaces or special characters)"
            )
            
            # Validate that contact number contains only digits
            if donor_contact_number and not donor_contact_number.isdigit():
                st.error("⚠️ Contact number must contain only numbers (0-9)")
                donor_contact_number = ""  # Clear invalid input
            
            donor_health_screening_completed = st.selectbox(
                "Health Screening Completed *",
                options=["", "Yes", "No"],
                help="Has the donor health screening been completed?"
            )
            
            donor_consent_form_completed = st.selectbox(
                "Consent Form Completed *",
                options=["", "Yes", "No"],
                help="Has the donor consent form been completed and signed?"
            )
        
        # Bottom section: Notes
        st.markdown("---")
        st.markdown("### 📝 Additional Notes")
        notes = st.text_area(
            "Additional observations or notes (optional):",
            placeholder="Enter any additional notes, observations, or issues that need attention...",
            height=100
        )
        
        # Form submission
        st.markdown("---")
        submitted = st.form_submit_button("📋 Submit Inspection Form", type="primary")
        
        if submitted:
            # Validate required fields
            errors = []
            
            if not inspector_name.strip():
                errors.append("Inspector Name is required")
            
            if not donation_chairs_condition:
                errors.append("Donation Chairs condition must be selected")
            if not blood_collection_equipment_condition:
                errors.append("Blood Collection Equipment condition must be selected")
            if not monitoring_devices_condition:
                errors.append("Monitoring Devices condition must be selected")
            if not safety_equipment_condition:
                errors.append("Safety Equipment condition must be selected")
            
            if not donor_name.strip():
                errors.append("Donor Name is required")
            if not donor_contact_number.strip():
                errors.append("Donor Contact Number is required")
            elif not donor_contact_number.isdigit():
                errors.append("Donor Contact Number must contain only numbers")
            elif len(donor_contact_number) < 8 or len(donor_contact_number) > 15:
                errors.append("Donor Contact Number must be between 8 and 15 digits")
            if not donor_health_screening_completed:
                errors.append("Health Screening Completed status must be selected")
            if not donor_consent_form_completed:
                errors.append("Consent Form Completed status must be selected")
            
            if errors:
                st.error("❌ Please fix the following errors:")
                for error in errors:
                    st.error(f"• {error}")
            else:
                # Submit the form
                with st.spinner("Submitting inspection form..."):
                    success = insert_form_data(
                        form_date=form_date,
                        inspector_name=inspector_name,
                        donation_chairs_condition=donation_chairs_condition,
                        blood_collection_equipment_condition=blood_collection_equipment_condition,
                        monitoring_devices_condition=monitoring_devices_condition,
                        safety_equipment_condition=safety_equipment_condition,
                        donor_name=donor_name,
                        donor_contact_number=donor_contact_number,
                        donor_health_screening_completed=(donor_health_screening_completed == "Yes"),
                        donor_consent_form_completed=(donor_consent_form_completed == "Yes"),
                        notes=notes,
                        user_email=user_email
                    )
                    
                    if success:
                        st.success("✅ Inspection form submitted successfully!")
                        st.balloons()
                        
                        # Show summary
                        st.markdown("### 📋 Submission Summary")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**📅 Form Information:**")
                            st.write(f"• **Date:** {form_date}")
                            st.write(f"• **Inspector:** {inspector_name}")
                            st.write(f"• **Submitted by:** {user_email}")
                            
                            st.markdown("**🔧 Equipment Status:**")
                            st.write(f"• **Donation Chairs:** {donation_chairs_condition}")
                            st.write(f"• **Blood Collection Equipment:** {blood_collection_equipment_condition}")
                            st.write(f"• **Monitoring Devices:** {monitoring_devices_condition}")
                            st.write(f"• **Safety Equipment:** {safety_equipment_condition}")
                        
                        with col2:
                            st.markdown("**🩸 Donor Information:**")
                            st.write(f"• **Name:** {donor_name}")
                            st.write(f"• **Contact:** {donor_contact_number}")
                            st.write(f"• **Health Screening:** {donor_health_screening_completed}")
                            st.write(f"• **Consent Form:** {donor_consent_form_completed}")
                            
                            if notes:
                                st.markdown("**📝 Notes:**")
                                st.write(notes)
                    else:
                        st.error("❌ Failed to submit form. Please try again or contact support.")
    
    # Show previous submissions from database ONLY
    st.markdown("---")
    st.subheader("📋 Recent Submissions")
    # st.caption(f"Showing exact content from `{get_table_name()}` table (read-only)")
    
    # Load from database only
    db_submissions = get_submissions_from_database()
    
    if db_submissions:
        st.info(f"📊 Found {len(db_submissions)} records in database table")
        
        # Display exact raw table content - all columns as they appear in the database
        raw_data = []
        for submission in db_submissions:
            raw_data.append({
                'id': submission['id'],
                'form_date': submission['form_date'],
                'inspector_name': submission['inspector_name'],
                'user_email': submission['user_email'],
                'submission_time': submission['submission_time'],
                'donation_chairs_condition': submission['donation_chairs_condition'],
                'blood_collection_equipment_condition': submission['blood_collection_equipment_condition'],
                'monitoring_devices_condition': submission['monitoring_devices_condition'],
                'safety_equipment_condition': submission['safety_equipment_condition'],
                'donor_name': submission['donor_name'],
                'donor_contact_number': submission['donor_contact_number'],
                'donor_health_screening_completed': 'Yes' if submission['donor_health_screening_completed'] else 'No',
                'donor_consent_form_completed': 'Yes' if submission['donor_consent_form_completed'] else 'No',
                'notes': submission['notes'],
                'created_at': submission['created_at'],
                'last_modified_time': submission['last_modified_time'],
                'last_modified_by': submission['last_modified_by'],
                'edit_reason': submission['edit_reason']
            })
        
        # Convert to DataFrame and display with exact column names from database
        df_raw = pd.DataFrame(raw_data)
        
        st.dataframe(
            df_raw,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "form_date": st.column_config.DateColumn("Form Date", width="medium"),
                "inspector_name": st.column_config.TextColumn("Inspector Name", width="medium"),
                "user_email": st.column_config.TextColumn("User Email", width="medium"),
                "submission_time": st.column_config.DatetimeColumn("Submission Time", width="medium"),
                "donation_chairs_condition": st.column_config.TextColumn("Donation Chairs", width="medium"),
                "blood_collection_equipment_condition": st.column_config.TextColumn("Blood Collection Equip", width="medium"),
                "monitoring_devices_condition": st.column_config.TextColumn("Monitoring Devices", width="medium"),
                "safety_equipment_condition": st.column_config.TextColumn("Safety Equipment", width="medium"),
                "donor_name": st.column_config.TextColumn("Donor Name", width="medium"),
                "donor_contact_number": st.column_config.TextColumn("Donor Contact", width="medium"),
                "donor_health_screening_completed": st.column_config.TextColumn("Health Screening", width="small"),
                "donor_consent_form_completed": st.column_config.TextColumn("Consent Form", width="small"),
                "notes": st.column_config.TextColumn("Notes", width="large"),
                "created_at": st.column_config.DatetimeColumn("Created At", width="medium"),
                "last_modified_time": st.column_config.DatetimeColumn("Last Modified", width="medium"),
                "last_modified_by": st.column_config.TextColumn("Modified By", width="medium"),
                "edit_reason": st.column_config.TextColumn("Edit Reason", width="large")
            }
        )
        
        # Show table info
        st.markdown("**Table Information:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(db_submissions))
        with col2:
            modified_records = sum(1 for s in db_submissions if s.get('last_modified_time'))
            st.metric("Modified Records", modified_records)
        with col3:
            unique_users = len(set(s['user_email'] for s in db_submissions))
            st.metric("Unique Users", unique_users)
    else:
        st.info("📝 No submissions found. Submit the form above to see data here.")
        st.caption(f"Data will be stored in `{get_table_name()}` table")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 0.8em;'>"
        "Lifeblood Red Cross Australia - Donor Center Management System<br>"
        "For technical support, contact your system administrator"
        "</div>", 
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Application startup error: {e}")
        st.write("Please contact your administrator or try refreshing the page.")
        import traceback
        st.code(traceback.format_exc())
