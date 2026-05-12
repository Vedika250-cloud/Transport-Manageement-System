from db import execute_query

queries = [
    "ALTER TABLE trips ADD COLUMN branch_id INT",
    "ALTER TABLE trips ADD FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE SET NULL",
    "UPDATE trips SET branch_id = 1 WHERE branch_id IS NULL",
    
    "ALTER TABLE consignments ADD COLUMN branch_id INT",
    "ALTER TABLE consignments ADD FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE SET NULL",
    "UPDATE consignments SET branch_id = 1 WHERE branch_id IS NULL",
    
    "ALTER TABLE payments ADD COLUMN branch_id INT",
    "ALTER TABLE payments ADD FOREIGN KEY (branch_id) REFERENCES branches(branch_id) ON DELETE SET NULL",
    "UPDATE payments SET branch_id = 1 WHERE branch_id IS NULL"
]

for q in queries:
    try:
        execute_query(q)
        print(f"Executed: {q}")
    except Exception as e:
        print(f"Failed {q}: {e}")
