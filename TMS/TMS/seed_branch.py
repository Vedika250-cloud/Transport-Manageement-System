from db import execute_query, execute_read

# Check if any branches exist
existing = execute_read("SELECT * FROM branches LIMIT 1")

if not existing:
    print("Creating default Central Operations branch...")
    # Insert default branch
    execute_query("INSERT INTO branches (branch_name) VALUES ('Central Operations')")
    
    # Get the branch ID
    branches = execute_read("SELECT branch_id FROM branches WHERE branch_name = 'Central Operations'")
    if branches:
        b_id = branches[0]['branch_id']
        print(f"Branch created with ID: {b_id}")
        
        print("Updating users...")
        try: execute_query(f"UPDATE users SET branch_id = {b_id} WHERE branch_id IS NULL")
        except Exception as e: print(e)
        
        print("Updating vehicles...")
        try: execute_query(f"UPDATE vehicles SET branch_id = {b_id} WHERE branch_id IS NULL")
        except Exception as e: print(e)
        
        print("Updating trips...")
        try: execute_query(f"UPDATE trips SET branch_id = {b_id} WHERE branch_id IS NULL")
        except Exception as e: print(e)
        
        print("Updating bookings...")
        try: execute_query(f"UPDATE bookings SET branch_id = {b_id} WHERE branch_id IS NULL")
        except Exception as e: print(e)
        
        print("Updating consignments...")
        try: execute_query(f"UPDATE consignments SET branch_id = {b_id} WHERE branch_id IS NULL")
        except Exception as e: print(e)
        
        print("Updating payments...")
        try: execute_query(f"UPDATE payments SET branch_id = {b_id} WHERE branch_id IS NULL")
        except Exception as e: print(e)
        
        print("Successfully assigned legacy records to Central Operations.")
else:
    print("Branches already exist, skipping seed.")
