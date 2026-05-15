import sys
import os

# Add parent directory to path to import db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import execute_query, execute_read

def migrate():
    print("Starting Payment Workflow Migration...")
    
    # Check if columns already exist in payments
    try:
        columns = execute_read("DESCRIBE payments", fetchall=True)
        col_names = [c['Field'] for c in columns]
        
        # Modify status and method ENUMs to VARCHAR for flexibility
        print("Modifying ENUM fields to VARCHAR...")
        execute_query("ALTER TABLE payments MODIFY COLUMN status VARCHAR(50) DEFAULT 'Pending'")
        execute_query("ALTER TABLE payments MODIFY COLUMN method VARCHAR(50) DEFAULT NULL")

        if 'advance_paid' not in col_names:
            print("Adding advance_paid to payments...")
            execute_query("ALTER TABLE payments ADD COLUMN advance_paid DECIMAL(10,2) DEFAULT 0")
            
        if 'remaining_amount' not in col_names:
            print("Adding remaining_amount to payments...")
            execute_query("ALTER TABLE payments ADD COLUMN remaining_amount DECIMAL(10,2) DEFAULT 0")

    except Exception as e:
        print(f"Error migrating payments table: {e}")

    # Check bookings table
    try:
        columns = execute_read("DESCRIBE bookings", fetchall=True)
        col_names = [c['Field'] for c in columns]
        
        print("Modifying shipment_status ENUM field to VARCHAR in bookings...")
        execute_query("ALTER TABLE bookings MODIFY COLUMN shipment_status VARCHAR(50) DEFAULT 'Pending'")

        if 'total_amount' not in col_names:
            print("Adding total_amount to bookings...")
            execute_query("ALTER TABLE bookings ADD COLUMN total_amount DECIMAL(10,2) DEFAULT 0")
            
        if 'advance_paid' not in col_names:
            print("Adding advance_paid to bookings...")
            execute_query("ALTER TABLE bookings ADD COLUMN advance_paid DECIMAL(10,2) DEFAULT 0")
            
        if 'remaining_amount' not in col_names:
            print("Adding remaining_amount to bookings...")
            execute_query("ALTER TABLE bookings ADD COLUMN remaining_amount DECIMAL(10,2) DEFAULT 0")

    except Exception as e:
        print(f"Error migrating bookings table: {e}")

    print("Migration Complete.")

if __name__ == "__main__":
    migrate()
