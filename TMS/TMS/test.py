import traceback
from db import execute_read

try:
    print("Testing query...")
    res = execute_read("""
        SELECT b.branch_name, 
               (SELECT COUNT(*) FROM trips t WHERE t.branch_id = b.branch_id) as total_trips,
               (SELECT IFNULL(SUM(amount), 0) FROM payments p WHERE p.branch_id = b.branch_id) as revenue
        FROM branches b
    """)
    print("Success:", res)
except Exception as e:
    print("Error occurred!")
    traceback.print_exc()
