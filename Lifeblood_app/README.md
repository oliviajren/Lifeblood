# Lifeblood Red Cross Australia - Donor Center Inspection App

A Databricks Asset Bundle (DAB) application for Lifeblood Red Cross Australia to digitize donor center equipment and compliance inspections.

## 🏥 About

This Streamlit application replaces manual paper-based inspections with a digital form that:
- Records equipment condition checks (donation chairs, blood collection equipment, monitoring devices, safety equipment)
- Captures donor compliance information (health screening, consent forms)
- Prevents duplicate submissions
- Stores all data in Unity Catalog Delta Lake for analysis and reporting

## 🚀 Deployment Guide for New Environments

### Prerequisites
- Databricks CLI installed and configured (`pip install databricks-cli`)
- Access to a Databricks workspace with Unity Catalog enabled
- SQL warehouse available for database operations
- Permissions to create catalogs, schemas, and tables in Unity Catalog

### 🔧 Required Configuration Changes

**IMPORTANT:** Before deploying, you MUST update these values for your environment:

#### 1. **Update `databricks.yml`** - Core Configuration
```yaml
# Line 8-10: Update warehouse configuration
variables:
  warehouse_http_path:
    default: "/sql/1.0/warehouses/YOUR_WAREHOUSE_ID"  # ⚠️ CHANGE THIS
  warehouse_id:
    default: "YOUR_WAREHOUSE_ID"                      # ⚠️ CHANGE THIS

# Line 18: Update catalog name (optional)
  catalog_name:
    default: "your_catalog_name"                      # Optional: change from 'livr'

# Line 32-33: Update schema configuration
resources:
  schemas:
    lifeblood_schema:
      catalog_name: ${var.catalog_name}               # Will use your catalog
      
# Line 43 & 63: Update warehouse ID in jobs and apps
    sql_task:
      warehouse_id: ${var.warehouse_id}               # Uses your warehouse
    sql_warehouse:
      id: ${var.warehouse_id}                         # Uses your warehouse

# Line 57 & 79: Update user permissions
permissions:
  - user_name: YOUR_EMAIL@company.com                 # ⚠️ CHANGE THIS
    level: CAN_MANAGE
```

#### 2. **Update `resources/create_table.sql`** - Database Permissions
```sql
-- Lines 41-44: Update user email for permissions
GRANT USAGE ON CATALOG livr TO `YOUR_EMAIL@company.com`;           -- ⚠️ CHANGE THIS
GRANT USAGE ON SCHEMA livr.lifeblood TO `YOUR_EMAIL@company.com`;  -- ⚠️ CHANGE THIS
GRANT SELECT ON TABLE livr.lifeblood.lifeblood_app TO `YOUR_EMAIL@company.com`;  -- ⚠️ CHANGE THIS
GRANT MODIFY ON TABLE livr.lifeblood.lifeblood_app TO `YOUR_EMAIL@company.com`;  -- ⚠️ CHANGE THIS
```

### 📋 Step-by-Step Deployment

#### Step 1: Get Your Warehouse ID
```bash
# List available warehouses
databricks warehouses list --profile YOUR_PROFILE

# Note the warehouse ID you want to use
```

#### Step 2: Clone and Configure
```bash
# Clone the repository
git clone https://github.com/oliviajren/Lifeblood.git
cd Lifeblood/Lifeblood_app

# Configure Databricks CLI (if not already done)
databricks configure --profile YOUR_PROFILE
```

#### Step 3: Update Configuration Files
1. **Edit `databricks.yml`:**
   - Replace `4b9b953939869799` with your warehouse ID
   - Replace `olivia.ren@databricks.com` with your email
   - Optionally change catalog name from `livr` to your preferred name

2. **Edit `resources/create_table.sql`:**
   - Replace `olivia.ren@databricks.com` with your email

#### Step 4: Deploy with Databricks Asset Bundle (DAB)
```bash
# Validate configuration
databricks bundle validate --profile YOUR_PROFILE

# Deploy infrastructure and app
databricks bundle deploy --profile YOUR_PROFILE

# Create database schema and table
databricks bundle run setup_database_job --profile YOUR_PROFILE

# Start the Streamlit app
databricks bundle run lifeblood_streamlit_app --profile YOUR_PROFILE
```

#### Step 5: Grant Service Principal Permissions
After deployment, the app's service principal needs database permissions:

```bash
# Get the app details to find service principal ID
databricks apps get lifeblood-form-app --profile YOUR_PROFILE

# Create grant files (replace SERVICE_PRINCIPAL_ID with actual ID from above)
echo '{"changes":[{"principal":"SERVICE_PRINCIPAL_ID","add":["USAGE"]}]}' > grants.json

# Grant permissions
databricks grants update catalog YOUR_CATALOG --json @grants.json --profile YOUR_PROFILE
databricks grants update schema YOUR_CATALOG.lifeblood --json @grants.json --profile YOUR_PROFILE

# For table permissions
echo '{"changes":[{"principal":"SERVICE_PRINCIPAL_ID","add":["SELECT","MODIFY"]}]}' > table_grants.json
databricks grants update table YOUR_CATALOG.lifeblood.lifeblood_app --json @table_grants.json --profile YOUR_PROFILE

# Clean up
rm grants.json table_grants.json
```

### 🎯 What is Databricks Asset Bundle (DAB)?

DAB is Infrastructure-as-Code for Databricks that allows you to:
- **Define** all resources (apps, jobs, schemas) in YAML files
- **Deploy** consistently across environments (dev/staging/prod)
- **Version control** your entire Databricks infrastructure
- **Manage** permissions and configurations centrally

**Key DAB Commands:**
```bash
databricks bundle validate    # Check configuration
databricks bundle deploy      # Deploy/update resources  
databricks bundle run <job>   # Execute specific jobs
databricks bundle destroy     # Remove all resources
```

The app will be available at: `https://YOUR_APP_NAME-WORKSPACE_ID.aws.databricksapps.com`

## 📁 Project Structure

```
Lifeblood_app/
├── databricks.yml              # DAB configuration
├── pyproject.toml              # Python package configuration
├── src/
│   └── Lifeblood_app/
│       ├── streamlit_app.py    # Main Streamlit application
│       └── app.yml             # App runtime configuration
├── resources/
│   └── create_table.sql        # Database schema setup
├── tests/                      # Unit tests
└── scripts/                    # Development utilities
```

## 🗄️ Database Schema

The application uses Unity Catalog with the following structure:
- **Catalog:** `livr`
- **Schema:** `lifeblood`
- **Table:** `lifeblood_app`

### Table Columns:
- Form metadata: `form_date`, `inspector_name`, `user_email`, `submission_time`
- Equipment conditions: `donation_chairs_condition`, `blood_collection_equipment_condition`, etc.
- Donor information: `donor_name`, `donor_contact_number`, compliance flags
- Additional: `notes`, `created_at`

## 🔧 Configuration

### Environment Variables
- `DATABRICKS_WAREHOUSE_HTTP_PATH`: SQL warehouse connection path

### Key Features
- **Duplicate Detection**: Prevents identical form submissions
- **User Authentication**: Automatic Databricks user detection
- **Data Validation**: Comprehensive form validation
- **Real-time Feedback**: Immediate submission confirmation

## 🧪 Development

### Local Development
```bash
# Install dependencies
pip install -e .

# Run tests
pytest tests/

# Local Streamlit (requires Databricks CLI configuration)
streamlit run src/Lifeblood_app/streamlit_app.py
```

### Bundle Commands
```bash
# Deploy to development
databricks bundle deploy

# Run the app
databricks bundle run lifeblood_streamlit_app

# Set up database
databricks bundle run setup_database_job

# Validate configuration
databricks bundle validate
```

## 📊 Usage

1. **Access the app** via the provided Databricks Apps URL
2. **Review the form guidance** at the top of the page
3. **Fill out the inspection form:**
   - Select inspection date and enter inspector name
   - Check equipment conditions (left side)
   - Enter donor compliance information (right side)
   - Add optional notes
4. **Submit the form** - duplicate detection will prevent identical submissions
5. **View recent submissions** in the table below the form

## 🔒 Security & Permissions

- User authentication via Databricks workspace login
- SQL injection prevention with parameterized queries
- Unity Catalog permissions for data access control
- App-level permissions for deployment and management

## 📈 Monitoring & Analytics

All form submissions are stored in Unity Catalog and can be analyzed using:
- Databricks SQL dashboards
- Notebook-based analytics
- CSV export functionality (built into the app)

## 🆘 Troubleshooting

### Common Issues and Solutions

#### 1. **"App Not Available" / 502 Bad Gateway**
- **Cause:** App failed to start or port configuration issue
- **Solution:** 
  ```bash
  # Check app status
  databricks apps get lifeblood-form-app --profile YOUR_PROFILE
  
  # Restart the app
  databricks bundle run lifeblood_streamlit_app --profile YOUR_PROFILE
  ```

#### 2. **"Insufficient Permissions" Database Error**
- **Cause:** Service principal lacks Unity Catalog permissions
- **Solution:** Follow Step 5 in deployment guide to grant permissions

#### 3. **"Warehouse ID not found" Error**
- **Cause:** Wrong warehouse ID in configuration
- **Solution:** 
  ```bash
  # List warehouses and get correct ID
  databricks warehouses list --profile YOUR_PROFILE
  # Update databricks.yml with correct warehouse_id
  ```

#### 4. **"Table/Schema Not Found" Error**
- **Cause:** Database setup job not run or failed
- **Solution:**
  ```bash
  # Re-run database setup
  databricks bundle run setup_database_job --profile YOUR_PROFILE
  ```

#### 5. **User Email Shows as Service Principal ID**
- **Cause:** User detection not working in Databricks Apps
- **Solution:** This is expected behavior - the app will detect the actual user email when accessed via Databricks Apps URL

### Getting Help
1. Check app logs in Databricks workspace under "Apps" section
2. Verify SQL warehouse is running and accessible
3. Ensure Unity Catalog permissions are correctly configured
4. Contact your Databricks administrator for workspace-level issues

## 📝 License

This project is developed for Lifeblood Red Cross Australia internal use.