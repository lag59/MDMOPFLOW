"""Seed demo projects into Apex Construction Group."""
import json, urllib.request, urllib.error

BASE = "https://mdmopflow-production-cd89.up.railway.app"
TENANT_ID = "dbd85ce9-2554-4110-819f-93e929697726"

def login(email):
    r = urllib.request.urlopen(urllib.request.Request(
        f"{BASE}/api/auth/login",
        data=json.dumps({"email": email, "password": "ChangeMe123!"}).encode(),
        headers={"Content-Type": "application/json"}, method="POST"))
    return json.loads(r.read())["tokens"]["access_token"]

def post(path, body, token):
    req = urllib.request.Request(
        f"{BASE}{path}", data=json.dumps(body).encode(),
        headers={"Content-Type":"application/json","Authorization":f"Bearer {token}","X-Tenant-ID":TENANT_ID},
        method="POST")
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8","ignore"))

token = login("permcheck@example.com")

PROJECTS = [
    {"project_name":"Highway 74 Drainage Phase 1","project_number":"PRJ-2026-001","customer":"NCDOT","address":"Hwy 74, Anson County, NC","project_manager":"Griffin Cole","start_date":"2026-09-01","end_date":"2026-12-15","contract_amount":"2850000","budget":"2420000","status":"active","description":"Stormwater infrastructure replacement along Hwy 74 corridor. 4,200 LF of 24-inch RCP and associated drainage structures."},
    {"project_name":"Apex Industrial Park Site Prep","project_number":"PRJ-2026-002","customer":"Apex Industrial LLC","address":"I-40 Business, Apex, NC","project_manager":"Griffin Cole","start_date":"2026-10-01","end_date":"2027-04-30","contract_amount":"4200000","budget":"3600000","status":"planning","description":"45-acre industrial park — site grading, utilities, access roads, and paving for Phase 2 development."},
    {"project_name":"Downtown Water Main Replacement","project_number":"PRJ-2026-003","customer":"City of Raleigh","address":"Fayetteville St, Raleigh, NC","project_manager":"Griffin Cole","start_date":"2026-08-15","end_date":"2026-11-30","contract_amount":"1950000","budget":"1700000","status":"active","description":"16-inch water main replacement through downtown corridor. Includes traffic control and road restoration."},
    {"project_name":"I-40 Interchange Earthwork","project_number":"PRJ-2026-004","customer":"NCDOT","address":"I-40 / Aviation Pkwy Interchange, Morrisville, NC","project_manager":"Griffin Cole","start_date":"2027-01-15","end_date":"2027-08-31","contract_amount":"5100000","budget":"4400000","status":"planning","description":"Mass earthwork and grading for I-40 interchange widening. 180,000 CY of cut/fill."},
    {"project_name":"Solar Farm Road & Pad Construction","project_number":"PRJ-2026-005","customer":"SunPath Energy","address":"Blue Ridge Pkwy area, Surry County, NC","project_manager":"Griffin Cole","start_date":"2026-09-15","end_date":"2027-02-28","contract_amount":"3800000","budget":"3200000","status":"active","description":"200-acre solar installation — access roads, panel pads, drainage, and erosion control."},
]

print("Creating projects...")
for proj in PROJECTS:
    s, b = post("/api/projects", proj, token)
    if s in (200, 201):
        print(f"  {s}  {proj['project_number']}  {proj['project_name'][:45]}")
    else:
        print(f"  {s}  {proj['project_number']}  {b.get('detail', b)}")

print("\nDone.")
