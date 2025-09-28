#!/usr/bin/env python3
"""
Test script to verify database connectivity and insert a test record
"""

from databricks.sdk import WorkspaceClient
import sys
from datetime import datetime

def test_database_connection():
    try:
        print("🔧 Testing database connection...")
        w = WorkspaceClient()
        
        # Test connection
        current_user = w.current_user.me()
        print(f"✅ Connected as: {current_user.user_name}")
        
        warehouse_id = "4b9b953939869799"
        table_name = "livr.lifeblood.lifeblood_app"
        
        # Test 1: Check if table exists
        print(f"📊 Checking table: {table_name}")
        count_query = f"SELECT COUNT(*) as count FROM {table_name}"
        
        response = w.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=count_query,
            wait_timeout="30s"
        )
        
        if response.status.state.value == "SUCCEEDED":
            if response.result and response.result.data_array:
                count = response.result.data_array[0][0]
                print(f"✅ Table exists with {count} records")
            else:
                print("✅ Table exists (empty)")
        else:
            print(f"❌ Failed to query table: {response.status}")
            return False
        
        # Test 2: Insert a test record
        print("🧪 Inserting test record...")
        test_time = datetime.now().isoformat()
        
        insert_query = f"""
        INSERT INTO {table_name} 
        (equipment_check, donor_condition, notes, user_email, submission_time)
        VALUES 
        (true, 'Test from script', 'Database connectivity test', '{current_user.user_name}', '{test_time}')
        """
        
        response = w.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=insert_query,
            wait_timeout="30s"
        )
        
        if response.status.state.value == "SUCCEEDED":
            print("✅ Test record inserted successfully!")
        else:
            print(f"❌ Failed to insert test record: {response.status}")
            return False
        
        # Test 3: Verify the insert
        print("🔍 Verifying insert...")
        verify_query = f"""
        SELECT equipment_check, donor_condition, notes, user_email, submission_time 
        FROM {table_name} 
        WHERE user_email = '{current_user.user_name}' 
        ORDER BY created_at DESC 
        LIMIT 1
        """
        
        response = w.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=verify_query,
            wait_timeout="30s"
        )
        
        if response.status.state.value == "SUCCEEDED":
            if response.result and response.result.data_array:
                row = response.result.data_array[0]
                print(f"✅ Verified record: Equipment={row[0]}, Condition='{row[1]}', User={row[3]}")
            else:
                print("⚠️ No records found after insert")
        
        print(f"""
🎉 Database connection test completed successfully!

📊 Summary:
   • Table: {table_name} ✅
   • Connection: Working ✅
   • Insert: Successful ✅
   • Warehouse: {warehouse_id} ✅
   
✅ The Streamlit app should now be able to write to the database!
        """)
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        print("\n💡 To fix this:")
        print("1. Configure Databricks CLI: databricks configure")
        print("2. Or set environment variables:")
        print("   export DATABRICKS_HOST='https://e2-demo-field-eng.cloud.databricks.com'")
        print("   export DATABRICKS_TOKEN='your-token'")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)


