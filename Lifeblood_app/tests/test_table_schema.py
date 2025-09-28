#!/usr/bin/env python3
"""
Test the new table schema
"""
from databricks.sdk import WorkspaceClient

def main():
    try:
        # Initialize Databricks client
        client = WorkspaceClient()
        
        print("🔍 Testing new table schema...")
        
        # Check table structure
        describe_query = "DESCRIBE TABLE livr.lifeblood.lifeblood_app"
        
        result = client.statement_execution.execute_statement(
            warehouse_id="4b9b953939869799",
            statement=describe_query,
            wait_timeout="30s"
        )
        
        if result.status.state.value == "SUCCEEDED":
            print("✅ Table exists! Current structure:")
            if hasattr(result.result, 'data_array') and result.result.data_array:
                for row in result.result.data_array:
                    print(f"  - {row[0]}: {row[1]}")
            
            # Test a simple insert to verify the schema works
            print("\n🧪 Testing insert with new schema...")
            test_insert = """
            INSERT INTO livr.lifeblood.lifeblood_app 
            (form_date, inspector_name, user_email, submission_time,
             donation_chairs_condition, blood_collection_equipment_condition, 
             monitoring_devices_condition, safety_equipment_condition,
             donor_name, donor_contact_number, donor_health_screening_completed, 
             donor_consent_form_completed, notes)
            VALUES 
            ('2025-09-28', 'Test Inspector', 'test@databricks.com', '2025-09-28T16:21:00',
             'Good', 'Good', 'Good', 'Good',
             'Test Donor', '123-456-7890', true, true, 'Test submission')
            """
            
            insert_result = client.statement_execution.execute_statement(
                warehouse_id="4b9b953939869799",
                statement=test_insert,
                wait_timeout="30s"
            )
            
            if insert_result.status.state.value == "SUCCEEDED":
                print("✅ Test insert successful!")
                
                # Query the data back
                select_query = "SELECT * FROM livr.lifeblood.lifeblood_app LIMIT 1"
                select_result = client.statement_execution.execute_statement(
                    warehouse_id="4b9b953939869799",
                    statement=select_query,
                    wait_timeout="30s"
                )
                
                if select_result.status.state.value == "SUCCEEDED":
                    print("✅ Test query successful!")
                    if hasattr(select_result.result, 'data_array') and select_result.result.data_array:
                        print("📊 Sample data:")
                        for i, row in enumerate(select_result.result.data_array[:1]):
                            print(f"  Row {i+1}: {row}")
                    
                    print("\n🎉 Database schema is working correctly!")
                else:
                    print(f"❌ Test query failed: {select_result.status}")
            else:
                print(f"❌ Test insert failed: {insert_result.status}")
        else:
            print(f"❌ Table describe failed: {result.status}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

