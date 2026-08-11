import sqlite3
import json
from pathlib import Path
from passlib.context import CryptContext

root = Path(r"c:\Users\libby\OneDrive\Desktop\mdm-opsflow-phase2-starter")
db_path = root / "mdm-opsflow-phase2-starter" / "backend" / "mdm_opsflow.db"

emails = [
    'est.94c289@example.com',
    'griffin@mdmopflow.com',
    'lag59@mdmopflow.com',
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

ctx = CryptContext(schemes=['pbkdf2_sha256'])
conn = sqlite3.connect(db_path)
rows = conn.execute(
    "SELECT email, display_name, title, platform_role, is_active, password_hash FROM users WHERE email IN ({0})".format(
        ','.join('?' for _ in emails)
    ),
    emails,
).fetchall()

for email, display_name, title, platform_role, is_active, password_hash in rows:
    verified = ctx.verify('ChangeMe123!', password_hash) if password_hash else None
    print(json.dumps({
        'email': email,
        'display_name': display_name,
        'title': title,
        'platform_role': platform_role,
        'is_active': bool(is_active),
        'password_matches_change_me_123': verified,
    }))

missing = [email for email in emails if not any(r[0] == email for r in rows)]
for email in missing:
    print(json.dumps({'email': email, 'found': False}))

conn.close()
