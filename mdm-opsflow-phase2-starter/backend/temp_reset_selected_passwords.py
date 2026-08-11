import sqlite3
from passlib.context import CryptContext

emails = [
    'live.est.29b6e3e5@example.com',
    'live.est.38e1713d@example.com',
    'live.est.bdcc16b5@example.com',
    'live.owner.22588ca4@example.com',
    'live.owner.29b6e3e5@example.com',
    'live.owner.3aa97967@example.com',
    'owner.8c515b@example.com',
    'permcheck2@example.com',
    'permcheck@example.com',
]

pwd_context = CryptContext(schemes=['pbkdf2_sha256'])
new_hash = pwd_context.hash('ChangeMe123!')

conn = sqlite3.connect('mdm_opsflow.db')
for email in emails:
    conn.execute('UPDATE users SET password_hash = ? WHERE email = ?', (new_hash, email))
conn.commit()
print('updated', len(emails))
conn.close()
