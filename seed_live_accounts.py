import json
import urllib.request
import urllib.error

BASE_URL = 'https://mdmopflow-production-cd89.up.railway.app'

accounts = [
    ('est.94c289@example.com', 'Estimator', 'ChangeMe123!'),
    ('griffin@mdmopflow.com', 'griffin', 'ChangeMe123!'),
    ('lag59@mdmopflow.com', 'lag59', 'ChangeMe123!'),
    ('live.est.29b6e3e5@example.com', 'Live Estimator', 'ChangeMe123!'),
    ('live.est.38e1713d@example.com', 'Live Estimator', 'ChangeMe123!'),
    ('live.est.bdcc16b5@example.com', 'Live Estimator', 'ChangeMe123!'),
    ('live.owner.22588ca4@example.com', 'Live Owner', 'ChangeMe123!'),
    ('live.owner.29b6e3e5@example.com', 'Live Owner', 'ChangeMe123!'),
    ('live.owner.3aa97967@example.com', 'Live Owner', 'ChangeMe123!'),
    ('owner.8c515b@example.com', 'Owner', 'ChangeMe123!'),
    ('permcheck2@example.com', 'Tester', 'ChangeMe123!'),
    ('permcheck@example.com', 'Tester', 'ChangeMe123!'),
]

for email, display_name, password in accounts:
    payload = json.dumps({'email': email, 'password': password, 'display_name': display_name}).encode('utf-8')
    req = urllib.request.Request(
        f'{BASE_URL}/api/auth/register',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode('utf-8')
            print(email, 'REGISTERED', resp.status)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', 'ignore')
        print(email, 'HTTP', exc.code, body)
    except Exception as exc:
        print(email, 'ERROR', repr(exc))
