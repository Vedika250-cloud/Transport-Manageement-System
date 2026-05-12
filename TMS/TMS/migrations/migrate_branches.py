import mysql.connector
import sys

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
        
        # 1. Backup existing branches table
        print("Creating backup table 'branches_backup'...")
        cur.execute("DROP TABLE IF EXISTS branches_backup")
        cur.execute("CREATE TABLE branches_backup AS SELECT * FROM branches")
        conn.commit()
        
        # 2. Extract location into city/state columns
        print("Extracting location to city and state...")
        cur.execute("SELECT branch_id, location, city, state FROM branches")
        branches = cur.fetchall()
        
        for branch in branches:
            loc = branch.get('location')
            b_id = branch['branch_id']
            city = branch.get('city')
            state = branch.get('state')
            
            if loc and (not city or not state):
                parts = [p.strip() for p in loc.split(',')]
                new_city = parts[0] if len(parts) > 0 else loc
                new_state = parts[1] if len(parts) > 1 else ''
                
                cur.execute("UPDATE branches SET city=%s, state=%s WHERE branch_id=%s", (new_city, new_state, b_id))
        
        conn.commit()
        print("Locations extracted.")
        
        # 3. Add branch_id foreign key to users table.
        print("Ensuring branch_id FK exists on users...")
        try:
            cur.execute("ALTER TABLE users ADD CONSTRAINT fk_user_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id)")
            conn.commit()
            print("Added foreign key fk_user_branch.")
        except mysql.connector.Error as err:
            print("FK ignored (likely exists or handled):", err)
        
        # 4. Remove redundant columns
        print("Removing redundant columns...")
        columns_to_drop = ['location', 'contact', 'contact_number', 'email', 'address']
        
        cur.execute("DESCRIBE branches")
        existing_cols = [row['Field'] for row in cur.fetchall()]
        
        for col in columns_to_drop:
            if col in existing_cols:
                cur.execute(f"ALTER TABLE branches DROP COLUMN {col}")
                print(f"Dropped column {col}")
        
        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur: cur.close()
        if conn: conn.close()

if __name__ == "__main__":
    migrate()
