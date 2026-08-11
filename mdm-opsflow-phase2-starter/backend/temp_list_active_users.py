import sqlite3
conn = sqlite3.connect('mdm_opsflow.db')
rows = conn.execute(
    "SELECT id, email, display_name, is_active, platform_role FROM users WHERE is_active = 1 ORDER BY email"
).fetchall()
print('COUNT', len(rows))
for row in rows:
    print(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}|{row[4]}")
conn.close()
