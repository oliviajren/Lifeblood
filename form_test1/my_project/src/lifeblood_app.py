import streamlit as st
import pandas as pd
from datetime import datetime, date
import uuid
import os
from databricks import sql
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Lifeblood Equipment Check",
    page_icon="🩸",
    layout="wide"
)

def get_db_connection():
    """Get database connection using Databricks SQL connector"""
    try:
        # Get warehouse URL from environment variable or use default
        warehouse_url = os.getenv('SQL_WAREHOUSE_URL', '/sql/1.0/warehouses/148ccb90800933a1')

        connection = sql.connect(
            server_hostname=os.getenv('DATABRICKS_SERVER_HOSTNAME'),
            http_path=warehouse_url,
            access_token=os.getenv('DATABRICKS_TOKEN')
        )
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        st.error(f"Database connection failed: {e}")
        return None

def insert_check_record(record_data):
    """Insert equipment check record into the database"""
    connection = get_db_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()

        insert_query = """
        INSERT INTO livr.lifeblood.equipment_check_log (
            check_id, check_date, shift_time, staff_name, staff_email,
            donation_chairs_functional, blood_pressure_monitors_calibrated,
            scales_accurate, refrigeration_temp_ok, centrifuge_functional,
            sterilization_equipment_ok, emergency_equipment_accessible,
            donor_screening_area_clean, collection_bags_supplies_adequate,
            safety_protocols_followed, staff_training_current,
            donor_comfort_facilities_ok, issues_found, corrective_actions,
            next_check_due, logged_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor.execute(insert_query, (
            record_data['check_id'],
            record_data['check_date'],
            record_data['shift_time'],
            record_data['staff_name'],
            record_data['staff_email'],
            record_data['donation_chairs_functional'],
            record_data['blood_pressure_monitors_calibrated'],
            record_data['scales_accurate'],
            record_data['refrigeration_temp_ok'],
            record_data['centrifuge_functional'],
            record_data['sterilization_equipment_ok'],
            record_data['emergency_equipment_accessible'],
            record_data['donor_screening_area_clean'],
            record_data['collection_bags_supplies_adequate'],
            record_data['safety_protocols_followed'],
            record_data['staff_training_current'],
            record_data['donor_comfort_facilities_ok'],
            record_data['issues_found'],
            record_data['corrective_actions'],
            record_data['next_check_due'],
            record_data['logged_at']
        ))

        connection.commit()
        cursor.close()
        connection.close()
        return True

    except Exception as e:
        logger.error(f"Failed to insert record: {e}")
        st.error(f"Failed to save record: {e}")
        return False

def main():
    """Main Streamlit app"""

    # Header
    st.title("🩸 Lifeblood Red Cross Australia")
    st.subheader("Blood Center Equipment Check Form")
    st.markdown("---")

    # Initialize session state
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False

    # Form
    with st.form("equipment_check_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Check Information")
            check_date = st.date_input("Check Date", value=date.today())
            shift_time = st.selectbox("Shift Time", ["Morning", "Afternoon", "Evening"])
            staff_name = st.text_input("Staff Name", placeholder="Enter your full name")
            staff_email = st.text_input("Staff Email", placeholder="Enter your email address")

        with col2:
            st.subheader("Next Check Information")
            next_check_due = st.date_input(
                "Next Check Due",
                value=date.today().replace(day=date.today().day + 7)
            )

        st.markdown("---")
        st.subheader("Equipment and Facility Checks")
        st.markdown("*Please check each item carefully and mark as functional/compliant*")

        # Equipment checks in organized sections
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Donation Equipment**")
            donation_chairs = st.checkbox("Donation chairs are functional", key="donation_chairs")
            bp_monitors = st.checkbox("Blood pressure monitors are calibrated", key="bp_monitors")
            scales = st.checkbox("Scales are accurate and functional", key="scales")
            centrifuge = st.checkbox("Centrifuge equipment is functional", key="centrifuge")

            st.markdown("**Safety & Emergency**")
            emergency_equipment = st.checkbox("Emergency equipment is accessible and functional", key="emergency")
            safety_protocols = st.checkbox("All safety protocols are being followed", key="safety")
            sterilization = st.checkbox("Sterilization equipment is working properly", key="sterilization")

        with col2:
            st.markdown("**Storage & Environment**")
            refrigeration = st.checkbox("Refrigeration units maintain proper temperature", key="refrigeration")
            screening_area = st.checkbox("Donor screening area is clean and organized", key="screening")
            comfort_facilities = st.checkbox("Donor comfort facilities are in good condition", key="comfort")

            st.markdown("**Supplies & Staff**")
            supplies = st.checkbox("Collection bags and supplies are adequate", key="supplies")
            training = st.checkbox("Staff training certifications are current", key="training")

        st.markdown("---")
        st.subheader("Additional Information")

        col1, col2 = st.columns(2)
        with col1:
            issues_found = st.text_area(
                "Issues Found (if any)",
                placeholder="Describe any issues or concerns identified during the check"
            )

        with col2:
            corrective_actions = st.text_area(
                "Corrective Actions Taken",
                placeholder="Describe any corrective actions taken to address issues"
            )

        # Submit button
        submitted = st.form_submit_button("Submit Equipment Check", type="primary")

        if submitted:
            # Validation
            if not staff_name or not staff_email:
                st.error("Please fill in your name and email address.")
                return

            if "@" not in staff_email:
                st.error("Please enter a valid email address.")
                return

            # Generate unique check ID
            check_id = str(uuid.uuid4())

            # Prepare record data
            record_data = {
                'check_id': check_id,
                'check_date': check_date,
                'shift_time': shift_time,
                'staff_name': staff_name,
                'staff_email': staff_email,
                'donation_chairs_functional': donation_chairs,
                'blood_pressure_monitors_calibrated': bp_monitors,
                'scales_accurate': scales,
                'refrigeration_temp_ok': refrigeration,
                'centrifuge_functional': centrifuge,
                'sterilization_equipment_ok': sterilization,
                'emergency_equipment_accessible': emergency_equipment,
                'donor_screening_area_clean': screening_area,
                'collection_bags_supplies_adequate': supplies,
                'safety_protocols_followed': safety_protocols,
                'staff_training_current': training,
                'donor_comfort_facilities_ok': comfort_facilities,
                'issues_found': issues_found if issues_found else None,
                'corrective_actions': corrective_actions if corrective_actions else None,
                'next_check_due': next_check_due,
                'logged_at': datetime.now()
            }

            # Save to database
            if insert_check_record(record_data):
                st.success("✅ Equipment check submitted successfully!")
                st.info(f"Check ID: {check_id}")
                st.session_state.form_submitted = True

                # Display summary
                st.markdown("---")
                st.subheader("Check Summary")

                # Count passed checks
                checks = [
                    donation_chairs, bp_monitors, scales, refrigeration,
                    centrifuge, sterilization, emergency_equipment,
                    screening_area, supplies, safety_protocols,
                    training, comfort_facilities
                ]
                passed_checks = sum(checks)
                total_checks = len(checks)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Checks Passed", f"{passed_checks}/{total_checks}")
                with col2:
                    st.metric("Success Rate", f"{(passed_checks/total_checks)*100:.1f}%")
                with col3:
                    st.metric("Next Check Due", next_check_due.strftime("%Y-%m-%d"))

                if issues_found:
                    st.warning(f"⚠️ Issues to address: {issues_found}")
            else:
                st.error("❌ Failed to submit equipment check. Please try again.")

    # Footer
    st.markdown("---")
    st.markdown(
        "🩸 **Lifeblood Red Cross Australia** | Equipment Check System | "
        "For technical support, contact your IT administrator."
    )

if __name__ == "__main__":
    main()