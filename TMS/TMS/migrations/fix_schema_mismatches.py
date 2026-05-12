import mysql.connector

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "lakshit",
    "database": "transport_management"
}

def migrate():
    try:
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor(dictionary=True)

        print("Checking bookings table schema...")
        cur.execute("DESCRIBE bookings")
        booking_cols = [row['Field'] for row in cur.fetchall()]
        
        if 'delivery_date' not in booking_cols:
            cur.execute("ALTER TABLE bookings ADD COLUMN delivery_date DATE NULL")
            print("Added delivery_date to bookings")
            
        if 'contact_info' not in booking_cols:
            cur.execute("ALTER TABLE bookings ADD COLUMN contact_info VARCHAR(255) NULL")
            print("Added contact_info to bookings")
            
        if 'branch_id' not in booking_cols:
            cur.execute("ALTER TABLE bookings ADD COLUMN branch_id INT DEFAULT 1")
            cur.execute("ALTER TABLE bookings ADD CONSTRAINT fk_booking_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE SET NULL")
            print("Added branch_id to bookings")

        print("Checking payments table schema...")
        cur.execute("DESCRIBE payments")
        payment_cols = [row['Field'] for row in cur.fetchall()]
        
        if 'Booking_id' not in payment_cols:
            cur.execute("ALTER TABLE payments ADD COLUMN Booking_id INT NULL")
            cur.execute("ALTER TABLE payments ADD CONSTRAINT fk_payment_booking FOREIGN KEY (Booking_id) REFERENCES bookings(booking_id) ON DELETE SET NULL")
            print("Added Booking_id to payments")

        conn.commit()
        print("Schema mismatches fixed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur: cur.close()
        if conn: conn.close()

if __name__ == "__main__":
    migrate()
