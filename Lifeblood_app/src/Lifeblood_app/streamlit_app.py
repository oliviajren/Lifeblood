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
    use_lakebase = os.getenv("USE_LAKEBASE", "false").lower() == "true"
    
    catalog = os.getenv("CATALOG_NAME", "livr")
    schema = os.getenv("SCHEMA_NAME", "lifeblood")
    
    if use_lakebase:
        # Use Lakebase Delta table (not synced table for writes)
        table = os.getenv("LAKEBASE_TABLE_NAME", "lifeblood_app_lb")
    else:
        # Use regular Delta table
        table = os.getenv("TABLE_NAME", "lifeblood_app")
    
    # Handle cases where variables weren't substituted properly
    if catalog and catalog.startswith("${"):
        catalog = "livr"
    if schema and schema.startswith("${"):
        schema = "lifeblood"
    if table and table.startswith("${"):
        table = "lifeblood_app_lb" if use_lakebase else "lifeblood_app"
    
    return f"{catalog}.{schema}.{table}"


def get_backend_info() -> dict:
    """Get information about the current backend configuration"""
    use_lakebase = os.getenv("USE_LAKEBASE", "false").lower() == "true"
    
    if use_lakebase:
        catalog = os.getenv("CATALOG_NAME", "livr")
        schema = os.getenv("SCHEMA_NAME", "lifeblood")
        synced_table = os.getenv("SYNCED_TABLE_NAME", "lifeblood_app_lb_synced")
        synced_table_full = f"{catalog}.{schema}.{synced_table}"
        
        return {
            "backend_type": "Lakebase Synced Table",
            "delta_table": get_table_name(),
            "synced_table": synced_table_full,
            "lakebase_instance": os.getenv("LAKEBASE_INSTANCE", "lifeblood_lakebase_instance"),
            "postgres_database": os.getenv("POSTGRES_DATABASE", "lifeblood_operational"),
            "sync_mode": "Continuous",
            "description": "Data is written to Delta table and synchronized in real-time to PostgreSQL via Lakebase"
        }
    else:
        return {
            "backend_type": "Delta Lake Table",
            "table_name": get_table_name(),
            "storage_format": "Delta Lake",
            "description": "Data is stored directly in Unity Catalog Delta Lake"
        }


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


def main():
    st.set_page_config(
        page_title="Lifeblood Red Cross Australia - Donor Center Check Form",
        page_icon="🩸",
        layout="wide"
    )
    
    # Header
    st.title("🩸 Lifeblood Red Cross Australia")
    st.header("Donor Center Equipment & Compliance Check Form")
    st.markdown("---")
    
    # Check authentication
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
    
    # Form Guidance - Prominent and Bold
    st.subheader("**FORM GUIDANCE**")
    st.warning("**IMPORTANT: Verify ALL required fields before submitting the form**")
    
    # Dropdown for detailed instructions
    with st.expander("📋 How to Complete This Inspection Form", expanded=False):
        st.markdown("""
        **Requirements:**
        - Fill in the form for all **required fields**. 
        - Any observations or issues can be added in the **Additional Notes** field.
      
        **Reminders:** 
        - All submissions are recorded with your user email and time of submission in the database.
        - If you need to submit on behalf of someone else, please override the user email in the **Advanced: Override User Email (if needed)** field.
        """)
    
    st.markdown("---")
    
    # Show welcome message with authenticated user
    st.success(f"👋 Welcome **{user_email}**!")
    st.caption("✅ Authenticated with Databricks")
    
    # Show backend information
    backend_info = get_backend_info()
    with st.expander("🗄️ Database Backend Information", expanded=False):
        st.markdown(f"**Backend Type:** {backend_info['backend_type']}")
        
        if backend_info['backend_type'] == "Lakebase Synced Table":
            st.markdown(f"**Delta Table:** `{backend_info['delta_table']}`")
            st.markdown(f"**Synced Table:** `{backend_info['synced_table']}`")
            st.markdown(f"**Lakebase Instance:** {backend_info['lakebase_instance']}")
            st.markdown(f"**PostgreSQL Database:** {backend_info['postgres_database']}")
            st.markdown(f"**Sync Mode:** {backend_info['sync_mode']}")
            st.info("🔄 " + backend_info['description'])
        else:
            st.markdown(f"**Table:** `{backend_info['table_name']}`")
            st.markdown(f"**Storage Format:** {backend_info['storage_format']}")
            st.info("📊 " + backend_info['description'])
    
    
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
    st.caption(f"Showing latest submissions from `{get_table_name()}`")
    
    # Load from database only
    db_submissions = load_recent_submissions_from_db()
    
    if db_submissions:
        st.info(f"📊 Loaded {len(db_submissions)} submissions from database")
        # Convert submissions to DataFrame for better display
        recent_submissions = db_submissions[-10:]  # Show last 10 submissions
        
        if recent_submissions:
            # Create DataFrame
            df_data = []
            for i, submission in enumerate(reversed(recent_submissions), 1):
                df_data.append({
                    '#': i,
                    'Form Date': str(submission['form_date']),
                    'Inspector': submission['inspector_name'],
                    'Donor Name': submission['donor_name'],
                    'Equipment Status': f"Chairs: {submission['donation_chairs_condition']}, Collection: {submission['blood_collection_equipment_condition']}",
                    'Compliance': f"Screening: {'✅' if submission['donor_health_screening_completed'] else '❌'}, Consent: {'✅' if submission['donor_consent_form_completed'] else '❌'}",
                    'Submitted By': submission['user_email'],
                    'Submission Time': submission['submission_time'][:19].replace('T', ' '),
                    'Notes': submission['notes'] if submission['notes'] else "—"
                })
            
            df = pd.DataFrame(df_data)
            
            # Display as interactive table
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "#": st.column_config.NumberColumn("ID", width="small"),
                    "Form Date": st.column_config.DateColumn("Date", width="small"),
                    "Inspector": st.column_config.TextColumn("Inspector", width="medium"),
                    "Donor Name": st.column_config.TextColumn("Donor", width="medium"),
                    "Equipment Status": st.column_config.TextColumn("Equipment", width="large"),
                    "Compliance": st.column_config.TextColumn("Compliance", width="medium"),
                    "Submitted By": st.column_config.TextColumn("User", width="medium"),
                    "Submission Time": st.column_config.DatetimeColumn("Submitted At", width="medium"),
                    "Notes": st.column_config.TextColumn("Notes", width="large")
                }
            )
            
            # Show summary statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                total_submissions = len(db_submissions)
                st.metric("Total Inspections", total_submissions)
            with col2:
                good_equipment = sum(1 for s in db_submissions if 
                                   all(cond == "Good" for cond in [
                                       s['donation_chairs_condition'],
                                       s['blood_collection_equipment_condition'],
                                       s['monitoring_devices_condition'],
                                       s['safety_equipment_condition']
                                   ]))
                st.metric("All Equipment Good", f"{good_equipment}/{total_submissions}")
            with col3:
                compliance_complete = sum(1 for s in db_submissions if 
                                        s['donor_health_screening_completed'] and 
                                        s['donor_consent_form_completed'])
                st.metric("Full Compliance", f"{compliance_complete}/{total_submissions}")
            
            # Option to download data as CSV
            csv_data = pd.DataFrame([{
                'form_date': s['form_date'],
                'inspector_name': s['inspector_name'],
                'user_email': s['user_email'],
                'submission_time': s['submission_time'],
                'donation_chairs_condition': s['donation_chairs_condition'],
                'blood_collection_equipment_condition': s['blood_collection_equipment_condition'],
                'monitoring_devices_condition': s['monitoring_devices_condition'],
                'safety_equipment_condition': s['safety_equipment_condition'],
                'donor_name': s['donor_name'],
                'donor_contact_number': s['donor_contact_number'],
                'donor_health_screening_completed': s['donor_health_screening_completed'],
                'donor_consent_form_completed': s['donor_consent_form_completed'],
                'notes': s['notes']
            } for s in db_submissions])
            
            csv = csv_data.to_csv(index=False)
            st.download_button(
                label="📥 Download All Submissions as CSV",
                data=csv,
                file_name=f"lifeblood_submissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
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
