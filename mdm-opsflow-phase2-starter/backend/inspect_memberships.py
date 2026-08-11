import sqlite3
import os

path = os.path.join(os.getcwd(), 'mdm_opsflow.db')
conn = sqlite3.connect(path)
cur = conn.cursor()
rows = []
rows.append('tenant_memberships rows:')
for row in cur.execute('SELECT id, user_id, tenant_id, role_id, status FROM tenant_memberships ORDER BY created_at'):
    rows.append(str(row))
rows.append('')
rows.append('roles:')
for row in cur.execute('SELECT id, tenant_id, name FROM roles ORDER BY name'):
    rows.append(str(row))
conn.close()

out_path = os.path.join(os.getcwd(), 'membership_inspection_output.txt')
with open(out_path, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(rows))
print(out_path)
