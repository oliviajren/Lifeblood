#!/usr/bin/env python3
"""
Minimal test app to isolate 502 issues
"""
import streamlit as st
import os

def main():
    st.title("🧪 Minimal Test App")
    st.write("If you can see this, the basic app is working!")
    
    # Test basic environment
    st.subheader("Environment Test")
    st.write(f"Python version: {st.__version__}")
    
    # Test headers
    st.subheader("Headers Test")
    try:
        if hasattr(st, 'context') and hasattr(st.context, 'headers'):
            headers = dict(st.context.headers)
            st.json(headers)
        else:
            st.write("No headers available")
    except Exception as e:
        st.error(f"Headers error: {e}")
    
    # Test environment variables
    st.subheader("Environment Variables")
    env_vars = {k: v for k, v in os.environ.items() if 'DATABRICKS' in k or k in ['USER', 'LOGNAME']}
    if env_vars:
        st.json(env_vars)
    else:
        st.write("No relevant environment variables found")
    
    # Test basic imports
    st.subheader("Import Test")
    try:
        from databricks.sdk import WorkspaceClient
        st.success("✅ databricks.sdk imported successfully")
    except Exception as e:
        st.error(f"❌ databricks.sdk import failed: {e}")
    
    try:
        import pandas as pd
        st.success("✅ pandas imported successfully")
    except Exception as e:
        st.error(f"❌ pandas import failed: {e}")

if __name__ == "__main__":
    main()
