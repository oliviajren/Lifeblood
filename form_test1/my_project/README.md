# Lifeblood Equipment Check Application

A Databricks Asset Bundle containing a Streamlit application for Lifeblood Red Cross Australia blood center equipment checks.

## Overview

This application replaces manual paper-based equipment checks with a digital form that:
- Captures comprehensive equipment and facility checks
- Stores data in a centralized Databricks Delta table
- Provides real-time validation and reporting
- Maintains audit trails for compliance

## Architecture

- **Database**: `livr.lifeblood.equipment_check_log` table in Databricks
- **Compute**: SQL Warehouse (`/sql/1.0/warehouses/148ccb90800933a1`)
- **Frontend**: Streamlit web application
- **Deployment**: Databricks Asset Bundle (DAB)

## Equipment Checks Covered

### Donation Equipment
- ✅ Donation chairs functionality
- ✅ Blood pressure monitor calibration
- ✅ Scale accuracy and functionality
- ✅ Centrifuge equipment operation

### Safety & Emergency
- ✅ Emergency equipment accessibility
- ✅ Safety protocol compliance
- ✅ Sterilization equipment operation

### Storage & Environment
- ✅ Refrigeration temperature maintenance
- ✅ Donor screening area cleanliness
- ✅ Donor comfort facilities condition

### Supplies & Staff
- ✅ Collection bags and supplies adequacy
- ✅ Staff training certification status

## Setup and Deployment

### Prerequisites
- Python 3.11+
- Databricks CLI configured
- Access to `livr` catalog in Databricks

### Local Development
```bash
# Install dependencies
pip install -e .

# Run locally (requires environment variables)
export DATABRICKS_SERVER_HOSTNAME="your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="your-token"
export SQL_WAREHOUSE_URL="/sql/1.0/warehouses/148ccb90800933a1"

python -m streamlit run src/lifeblood_app.py
```

### Deploy to Databricks
```bash
# Validate the bundle
databricks bundle validate

# Deploy to development
databricks bundle deploy --target dev

# Launch the Streamlit app
databricks bundle run lifeblood_equipment_check
```

## Database Schema

The application writes to `livr.lifeblood.equipment_check_log` with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `check_id` | STRING | Unique identifier for each check |
| `check_date` | DATE | Date of equipment check |
| `shift_time` | STRING | Shift (Morning/Afternoon/Evening) |
| `staff_name` | STRING | Name of staff performing check |
| `staff_email` | STRING | Email of staff performing check |
| `donation_chairs_functional` | BOOLEAN | Donation chairs status |
| `blood_pressure_monitors_calibrated` | BOOLEAN | BP monitor calibration status |
| `scales_accurate` | BOOLEAN | Scale accuracy status |
| `refrigeration_temp_ok` | BOOLEAN | Refrigeration temperature status |
| `centrifuge_functional` | BOOLEAN | Centrifuge functionality |
| `sterilization_equipment_ok` | BOOLEAN | Sterilization equipment status |
| `emergency_equipment_accessible` | BOOLEAN | Emergency equipment accessibility |
| `donor_screening_area_clean` | BOOLEAN | Screening area cleanliness |
| `collection_bags_supplies_adequate` | BOOLEAN | Supplies adequacy |
| `safety_protocols_followed` | BOOLEAN | Safety protocol compliance |
| `staff_training_current` | BOOLEAN | Staff training status |
| `donor_comfort_facilities_ok` | BOOLEAN | Comfort facilities status |
| `issues_found` | STRING | Description of issues (optional) |
| `corrective_actions` | STRING | Corrective actions taken (optional) |
| `next_check_due` | DATE | Next scheduled check date |
| `logged_at` | TIMESTAMP | System timestamp of record creation |

## Configuration

The application uses the following DAB variables:

```yaml
variables:
  sql_warehouse_url:
    description: "SQL Warehouse URL for Lifeblood equipment check app"
    default: "/sql/1.0/warehouses/148ccb90800933a1"
```

## Security

- User authentication via Databricks workspace SSO
- Data encrypted in transit and at rest
- Audit logging of all form submissions
- Row-level security through staff email tracking

## Support

For technical issues:
1. Check Databricks workspace connectivity
2. Verify SQL warehouse accessibility
3. Confirm table permissions in `livr.lifeblood` schema
4. Contact your Databricks administrator

## Compliance

This application maintains records for regulatory compliance including:
- Equipment check frequencies
- Staff certification tracking
- Issue resolution documentation
- Complete audit trails
