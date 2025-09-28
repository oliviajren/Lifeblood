# Tests Directory

This directory contains unit tests and integration tests for the Lifeblood Red Cross Donor Center Form application.

## Test Structure

```
tests/
├── __init__.py                    # Tests package init
├── README.md                     # This file
├── test_minimal.py               # Minimal app test for deployment verification
├── test_database_connection.py   # Database connectivity and integration tests
├── test_new_user_detection.py    # User authentication detection tests
├── test_table_schema.py          # Database schema validation tests
└── fixtures/                     # Test data and fixtures (to be added)
```

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-cov streamlit

# Or using uv
uv pip install pytest pytest-cov streamlit
```

### Run All Tests
```bash
# From project root
pytest tests/

# With coverage
pytest tests/ --cov=src/Lifeblood_app
```

### Run Specific Tests
```bash
# Test database connectivity
pytest tests/test_database_connection.py

# Test user detection
pytest tests/test_new_user_detection.py

# Test table schema
pytest tests/test_table_schema.py

# Test minimal app deployment
pytest tests/test_minimal.py
```

## Test Categories

### Unit Tests
- Test individual functions and components
- Mock external dependencies
- Fast execution

### Integration Tests
- Test database connectivity
- Test Databricks SDK integration
- Test end-to-end workflows

### UI Tests
- Test Streamlit app functionality
- Test form validation
- Test user interactions

## Test Data

Test fixtures and sample data should be placed in:
- `tests/fixtures/` - Static test data files
- Individual test files - Small inline test data

## Best Practices

1. **Naming**: Test files should start with `test_`
2. **Structure**: Mirror the source code structure
3. **Isolation**: Each test should be independent
4. **Mocking**: Mock external services (Databricks, databases)
5. **Coverage**: Aim for high test coverage
6. **Documentation**: Document complex test scenarios

## Future Test Implementation

The following tests should be implemented:

### `test_streamlit_app.py`
- Test form validation
- Test user authentication detection
- Test data submission
- Test UI components

### `test_database.py`
- Test database connection
- Test table creation
- Test data insertion
- Test data retrieval
- Test error handling

### `test_integration.py`
- Test end-to-end form submission
- Test database integration
- Test authentication flow

## Continuous Integration

Tests should be run in CI/CD pipeline:
```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pip install -e .
    pytest tests/ --cov=src/Lifeblood_app --cov-report=xml
```


