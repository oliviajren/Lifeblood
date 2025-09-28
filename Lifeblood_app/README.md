# Lifeblood Red Cross Australia - Donor Center Inspection App

A Databricks Asset Bundle (DAB) application for Lifeblood Red Cross Australia to digitize donor center equipment and compliance inspections.

## 🏥 About

This Streamlit application replaces manual paper-based inspections with a digital form that:
- Records equipment condition checks (donation chairs, blood collection equipment, monitoring devices, safety equipment)
- Captures donor compliance information (health screening, consent forms)
- Prevents duplicate submissions
- Stores all data in Unity Catalog for analysis and reporting

## 🚀 Quick Start

### Prerequisites
- Databricks CLI installed and configured
- Access to a Databricks workspace with Unity Catalog
- SQL warehouse available for database operations

### Deployment

1. **Clone and navigate to the project:**
   ```bash
   git clone <repository-url>
   cd Lifeblood_app
   ```

2. **Configure your Databricks profile:**
   ```bash
   databricks configure --profile dev
   ```

3. **Deploy the application:**
   ```bash
   databricks bundle deploy --profile dev
   ```

4. **Set up the database:**
   ```bash
   databricks bundle run setup_database_job --profile dev
   ```

5. **Start the Streamlit app:**
   ```bash
   databricks bundle run lifeblood_streamlit_app --profile dev
   ```

The app will be available at the URL provided in the output.

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

## 🆘 Support

For technical issues:
1. Check the app logs in Databricks workspace
2. Verify SQL warehouse connectivity
3. Ensure proper Unity Catalog permissions
4. Contact your Databricks administrator

## 📝 License

This project is developed for Lifeblood Red Cross Australia internal use.