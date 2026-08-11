import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['pbkdf2_sha256'])
new_password = 'ChangeMe123!'
new_hash = pwd_context.hash(new_password)

conn = sqlite3.connect('mdm_opsflow.db')
conn.execute('UPDATE users SET password_hash = ? WHERE 1=1', (new_hash,))
conn.commit()
count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
print('updated', count)
conn.close()
