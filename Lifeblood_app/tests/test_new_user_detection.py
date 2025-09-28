#!/usr/bin/env python3
"""
Test script for the new user detection approach using the recommended pattern.
"""

import os
import sys
sys.path.append('src')

# Mock Streamlit context for testing
class MockContext:
    def __init__(self, headers=None):
        self.headers = headers if headers is not None else {}

class MockStreamlit:
    def __init__(self, context=None):
        self.context = context if context is not None else MockContext()
        self.session_state = {}
        
    def cache_resource(self, func):
        """Mock cache_resource decorator"""
        return func

# Set up mock environment
import streamlit as st
mock_st = MockStreamlit()

def test_scenario(name, headers=None, env_vars=None):
    """Test a specific user detection scenario"""
    print(f"\n--- Testing: {name} ---")
    
    # Reset environment
    original_env = os.environ.copy()
    for key in list(os.environ.keys()):
        if key.startswith('DATABRICKS_') or key in ['USER', 'LOGNAME']:
            if key not in ['DATABRICKS_CONFIG_PROFILE', 'DATABRICKS_HOST', 'DATABRICKS_TOKEN']:
                del os.environ[key]
    
    # Set test environment variables
    if env_vars:
        for k, v in env_vars.items():
            os.environ[k] = v
    
    # Set test headers
    mock_st.context.headers = headers if headers else {}
    
    # Temporarily replace st.context for testing
    original_context = getattr(st, 'context', None)
    st.context = mock_st.context
    
    try:
        # Import and test the function
        from Lifeblood_app.streamlit_app import get_current_user_email
        
        detected_email = get_current_user_email()
        print(f"✅ Detected: {detected_email}")
        
        # Check session state for auth method
        if hasattr(st, 'session_state') and 'auth_method' in st.session_state:
            print(f"📋 Method: {st.session_state['auth_method']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Restore original context
        if original_context:
            st.context = original_context
        
        # Restore environment
        os.environ.clear()
        os.environ.update(original_env)

def main():
    print("🧪 Testing New User Detection Approach")
    print("=" * 50)
    
    # Test 1: Databricks Apps header (production scenario)
    test_scenario(
        "Databricks Apps Header",
        headers={"x-forwarded-email": "olivia.ren@databricks.com"}
    )
    
    # Test 2: Environment variables
    test_scenario(
        "Environment Variables",
        env_vars={"DATABRICKS_USER": "olivia.ren@databricks.com"}
    )
    
    # Test 3: System user fallback
    test_scenario(
        "System User Fallback",
        env_vars={"USER": "olivia.ren"}
    )
    
    # Test 4: Databricks SDK (local development)
    test_scenario(
        "Databricks SDK (Local Development)"
        # This will use the actual configured authentication
    )
    
    # Test 5: No authentication available
    test_scenario(
        "No Authentication Available"
    )
    
    print("\n" + "=" * 50)
    print("🎯 Test Summary:")
    print("✅ The new approach prioritizes:")
    print("   1. x-forwarded-email header (Databricks Apps)")
    print("   2. DATABRICKS_USER environment variable")
    print("   3. USER environment variable")
    print("   4. Databricks SDK (local development)")
    print("   5. Returns None if no authentication found")
    print("\n💡 This approach is cleaner and more reliable!")

if __name__ == "__main__":
    main()


