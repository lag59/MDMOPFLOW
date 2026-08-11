import sqlite3
conn = sqlite3.connect('mdm_opsflow.db')
rows = conn.execute(
    "SELECT id, email, display_name, is_active, password_hash FROM users ORDER BY email"
).fetchall()
print('COUNT', len(rows))
for row in rows:
    print(f"{row[1]}|{row[2]}|{row[3]}|{row[4]}")
conn.close()
