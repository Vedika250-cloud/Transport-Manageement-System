import mysql.connector
from mysql.connector import pooling
import logging

# Configure basic logging for DB errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "lakshit",
    "database": "transport_management",
    "charset": "utf8mb4"
}

# Initialize connection pool
try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="tms_pool",
        pool_size=10,
        pool_reset_session=True,
        **db_config
    )
except Exception as e:
    logger.error(f"Error creating connection pool: {e}")
    connection_pool = None

def get_db_connection():
    if connection_pool:
        try:
            return connection_pool.get_connection()
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            # Fallback to direct connection if pool fails
            return mysql.connector.connect(**db_config)
    else:
        return mysql.connector.connect(**db_config)

# For backwards compatibility during transition
def dbconnect():
    return get_db_connection()

def execute_read(query, params=None, dictionary=True, fetchall=True):
    """Helper for SELECT queries. Handles connection, cursor, execution, and cleanup."""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=dictionary, buffered=True)
        cur.execute(query, params or ())
        if fetchall:
            return cur.fetchall()
        else:
            return cur.fetchone()
    except Exception as e:
        logger.error(f"Database read error: {e}\nQuery: {query}\nParams: {params}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def execute_query(query, params=None):
    """Helper for INSERT, UPDATE, DELETE queries. Handles connection, cursor, execution, commit, and cleanup."""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(buffered=True)
        cur.execute(query, params or ())
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database write error: {e}\nQuery: {query}\nParams: {params}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def verify_database_schema():
    """Verify that required tables exist on app startup."""
    required_tables = ['users', 'vehicles', 'trips', 'bookings', 'consignments', 'payments']
    missing_tables = []
    try:
        tables = execute_read("SHOW TABLES", fetchall=True, dictionary=False)
        existing_tables = [table[0] for table in tables]
        
        for rt in required_tables:
            if rt not in existing_tables:
                missing_tables.append(rt)
                
        if missing_tables:
            logger.error(f"Schema mismatch! Missing tables: {', '.join(missing_tables)}")
        
        # Run Branch Migration
        if 'branches' not in existing_tables:
            logger.info("Running branch hierarchy migration...")
            
            # 1. Create branches table
            execute_query("""
            CREATE TABLE branches (
                branch_id INT AUTO_INCREMENT PRIMARY KEY,
                branch_name VARCHAR(255) NOT NULL,
                city VARCHAR(100),
                state VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # 2. Insert Central Operations
            execute_query("INSERT INTO branches (branch_id, branch_name, city, state) VALUES (1, 'Central Operations', 'HQ City', 'HQ State')")
            
            # 3. Add branch_id to existing tables
            for table in required_tables:
                try:
                    execute_query(f"ALTER TABLE {table} ADD COLUMN branch_id INT DEFAULT 1")
                    execute_query(f"UPDATE {table} SET branch_id = 1 WHERE branch_id IS NULL")
                    execute_query(f"ALTER TABLE {table} ADD CONSTRAINT fk_{table}_branch FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE SET NULL")
                except Exception as e:
                    logger.error(f"Error migrating table {table}: {e}")
            
            logger.info("Branch migration successfully applied.")
        else:
            logger.info("Database schema verification passed. Core tables and branches exist.")
            
    except Exception as e:
        logger.error(f"Failed to verify database schema: {e}")