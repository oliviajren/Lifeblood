-- Create the lifeblood schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS livr.lifeblood;

-- Create the equipment_check_log table
CREATE TABLE IF NOT EXISTS livr.lifeblood.equipment_check_log (
    check_id STRING NOT NULL COMMENT 'Unique identifier for each equipment check',
    check_date DATE NOT NULL COMMENT 'Date when the equipment check was performed',
    shift_time STRING NOT NULL COMMENT 'Shift time (Morning/Afternoon/Evening)',
    staff_name STRING NOT NULL COMMENT 'Name of staff member performing the check',
    staff_email STRING NOT NULL COMMENT 'Email of staff member performing the check',

    -- Equipment checks
    donation_chairs_functional BOOLEAN NOT NULL COMMENT 'All donation chairs are functional',
    blood_pressure_monitors_calibrated BOOLEAN NOT NULL COMMENT 'Blood pressure monitors are calibrated',
    scales_accurate BOOLEAN NOT NULL COMMENT 'Scales are accurate and functional',
    refrigeration_temp_ok BOOLEAN NOT NULL COMMENT 'Refrigeration units maintain proper temperature',
    centrifuge_functional BOOLEAN NOT NULL COMMENT 'Centrifuge equipment is functional',
    sterilization_equipment_ok BOOLEAN NOT NULL COMMENT 'Sterilization equipment is working properly',
    emergency_equipment_accessible BOOLEAN NOT NULL COMMENT 'Emergency equipment is accessible and functional',
    donor_screening_area_clean BOOLEAN NOT NULL COMMENT 'Donor screening area is clean and organized',
    collection_bags_supplies_adequate BOOLEAN NOT NULL COMMENT 'Collection bags and supplies are adequate',
    safety_protocols_followed BOOLEAN NOT NULL COMMENT 'All safety protocols are being followed',
    staff_training_current BOOLEAN NOT NULL COMMENT 'Staff training certifications are current',
    donor_comfort_facilities_ok BOOLEAN NOT NULL COMMENT 'Donor comfort facilities are in good condition',

    -- Optional fields
    issues_found STRING COMMENT 'Description of any issues found during the check',
    corrective_actions STRING COMMENT 'Corrective actions taken for any issues',

    -- Scheduling and audit
    next_check_due DATE NOT NULL COMMENT 'Date when the next check is due',
    logged_at TIMESTAMP NOT NULL COMMENT 'Timestamp when the record was logged into the system'
)
USING DELTA
COMMENT 'Equipment check log for Lifeblood Red Cross Australia blood centers';