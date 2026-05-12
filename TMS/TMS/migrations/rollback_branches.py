import mysql.connector

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "lakshit",
    "database": "transport_management"
}

def rollback():
    try:
        conn = mysql.connector.connect(**db_config)
        cur = conn.cursor()
        
        print("Checking for backup table...")
        cur.execute("SHOW TABLES LIKE 'branches_backup'")
        if not cur.fetchone():
            print("Backup table 'branches_backup' not found. Cannot rollback.")
            return
            
        print("Restoring branches from backup...")
        # Temporarily disable foreign key checks to drop and restore
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute("DROP TABLE branches")
        cur.execute("CREATE TABLE branches AS SELECT * FROM branches_backup")
        
        # Re-add primary key and auto increment
        cur.execute("ALTER TABLE branches ADD PRIMARY KEY (branch_id)")
        cur.execute("ALTER TABLE branches MODIFY branch_id INT AUTO_INCREMENT")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
        
        conn.commit()
        print("Rollback completed successfully.")
        
    except Exception as e:
        print(f"Rollback failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur: cur.close()
        if conn: conn.close()

if __name__ == "__main__":
    rollback()
