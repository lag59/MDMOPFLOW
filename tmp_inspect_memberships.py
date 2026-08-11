import sqlite3
conn = sqlite3.connect(r'C:\Users\libby\OneDrive\Desktop\mdm-opsflow-phase2-starter\mdm-opsflow-phase2-starter\backend\mdm_opsflow.db')
rows = conn.execute('''
select tm.id, tm.user_id, tm.tenant_id, tm.role_id, tm.status, r.name
from tenant_memberships tm
left join roles r on r.id = tm.role_id
order by tm.user_id, tm.tenant_id, r.name
''').fetchall()
for row in rows:
    print(row)
conn.close()
