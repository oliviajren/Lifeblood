import streamlit as st
import pandas as pd
from datetime import datetime, date
import uuid
import os

# Page configuration
st.set_page_config(
    page_title="Lifeblood Donor Center Compliance Form",
    page_icon="🩸",
    layout="wide"
)

def main():
    """Main Streamlit app"""

    # Header
    st.title("🩸 Lifeblood Red Cross Australia")
    st.subheader("Donor Center Compliance Form")
    st.markdown("---")

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
                value=date.today().replace(day=min(date.today().day + 7, 28))
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

            # Create summary data
            checks = [
                donation_chairs, bp_monitors, scales, refrigeration,
                centrifuge, sterilization, emergency_equipment,
                screening_area, supplies, safety_protocols,
                training, comfort_facilities
            ]
            passed_checks = sum(checks)
            total_checks = len(checks)

            # Show success message (since we can't connect to database in this demo)
            st.success("✅ Equipment check submitted successfully!")
            st.info(f"Check ID: {check_id}")

            # Display summary
            st.markdown("---")
            st.subheader("Check Summary")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Checks Passed", f"{passed_checks}/{total_checks}")
            with col2:
                st.metric("Success Rate", f"{(passed_checks/total_checks)*100:.1f}%")
            with col3:
                st.metric("Next Check Due", next_check_due.strftime("%Y-%m-%d"))

            if issues_found:
                st.warning(f"⚠️ Issues to address: {issues_found}")

            # Create a summary dataframe
            check_data = {
                "Check ID": [check_id],
                "Date": [check_date],
                "Shift": [shift_time],
                "Staff": [staff_name],
                "Email": [staff_email],
                "Checks Passed": [f"{passed_checks}/{total_checks}"],
                "Issues": [issues_found if issues_found else "None"],
                "Actions": [corrective_actions if corrective_actions else "None"],
                "Next Due": [next_check_due]
            }

            df = pd.DataFrame(check_data)
            st.subheader("Form Data Summary")
            st.dataframe(df, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown(
        "🩸 **Lifeblood Red Cross Australia** | Equipment Check System | "
        "For technical support, contact your IT administrator."
    )

if __name__ == "__main__":
    main()