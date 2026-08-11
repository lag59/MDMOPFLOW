"""
Seed demo tenants and memberships against the live Railway backend.
- Each owner account completes onboarding to create its own tenant.
- Estimators and testers are then assigned to those tenants via the admin API.
"""
import json
import urllib.request
import urllib.error

BASE = "https://mdmopflow-production-cd89.up.railway.app"
PASSWORD = "ChangeMe123!"

TENANTS = [
    {
        "owner_email": "live.owner.22588ca4@example.com",
        "company_name": "Apex Construction Group",
        "company_types": ["General Contractor"],
        "modules": ["projects", "tickets", "intake", "estimator", "payroll"],
    },
    {
        "owner_email": "live.owner.29b6e3e5@example.com",
        "company_name": "BlueStar Builders",
        "company_types": ["General Contractor"],
        "modules": ["projects", "tickets", "intake", "estimator"],
    },
    {
        "owner_email": "live.owner.3aa97967@example.com",
        "company_name": "Crestline Contracting",
        "company_types": ["Specialty Contractor"],
        "modules": ["projects", "tickets", "daily_field_reports"],
    },
    {
        "owner_email": "owner.8c515b@example.com",
        "company_name": "Desert Ridge Development",
        "company_types": ["Heavy Civil"],
        "modules": ["projects", "tickets", "estimator", "customer_portal"],
    },
]

# Which users to assign into which tenant (by company name) and what role
MEMBERSHIPS = [
    ("live.est.29b6e3e5@example.com",  "Apex Construction Group",   "estimator"),
    ("live.est.38e1713d@example.com",  "BlueStar Builders",          "estimator"),
    ("live.est.bdcc16b5@example.com",  "Crestline Contracting",      "estimator"),
    ("est.94c289@example.com",          "Desert Ridge Development",   "estimator"),
    ("permcheck@example.com",           "Apex Construction Group",    "project_manager"),
    ("permcheck2@example.com",          "BlueStar Builders",          "project_manager"),
]


def post(url, body, token=None):
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8", "ignore"))


def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def login(email):
    status, body = post(f"{BASE}/api/auth/login", {"email": email, "password": PASSWORD})
    if status != 200:
        raise RuntimeError(f"Login failed for {email}: {body}")
    return body["tokens"]["access_token"]


# Step 1 — admin token
print("=== Logging in as super admin ===")
admin_token = login("lag59@mdmopflow.com")
print("OK")

# Step 2 — get all platform users so we can look up IDs
print("\n=== Fetching user list ===")
users = get(f"{BASE}/api/admin/users", admin_token)
user_by_email = {u["email"]: u for u in users}
print(f"Found {len(users)} users")

# Step 3 — onboard each owner to create their tenant
tenant_by_name = {}
print("\n=== Creating tenants via onboarding ===")
for cfg in TENANTS:
    email = cfg["owner_email"]
    try:
        token = login(email)
    except RuntimeError as exc:
        print(f"  SKIP {email}: {exc}")
        continue

    status, body = post(
        f"{BASE}/api/onboarding/complete",
        {
            "company_name": cfg["company_name"],
            "company_types": cfg["company_types"],
            "language": "en",
            "modules": cfg["modules"],
            "first_project_name": f"{cfg['company_name']} — First Project",
        },
        token=token,
    )
    if status == 201:
        tid = body["tenant_id"]
        tenant_by_name[cfg["company_name"]] = tid
        print(f"  CREATED  {cfg['company_name']}  tenant_id={tid}")
    elif status == 400 and "already completed" in str(body):
        # Tenant exists — fetch it from admin API
        print(f"  EXISTS   {cfg['company_name']} — fetching tenant id...")
        tenants_resp = get(f"{BASE}/api/core-platform/tenants", admin_token)
        for t in tenants_resp:
            if t["name"] == cfg["company_name"]:
                tenant_by_name[cfg["company_name"]] = t["id"]
                print(f"           found tenant_id={t['id']}")
                break
    else:
        print(f"  ERROR    {cfg['company_name']}: {status} {body}")

# Step 4 — assign memberships
print("\n=== Assigning roles ===")
for email, company, role in MEMBERSHIPS:
    user = user_by_email.get(email)
    tenant_id = tenant_by_name.get(company)
    if not user:
        print(f"  SKIP {email}: user not found")
        continue
    if not tenant_id:
        print(f"  SKIP {email} → {company}: tenant not found")
        continue

    status, body = post(
        f"{BASE}/api/admin/users/{user['id']}/memberships",
        {"tenant_id": tenant_id, "role_name": role},
        token=admin_token,
    )
    if status in (200, 201):
        print(f"  ASSIGNED {email} → {company} as {role}")
    else:
        print(f"  ERROR    {email} → {company}: {status} {body}")

print("\nDone.")
