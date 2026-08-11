"""Seed demo estimates and bid pipeline items into Apex Construction Group."""
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

token = login("live.est.29b6e3e5@example.com")

ESTIMATES = [
    {"estimate_name":"Highway 74 Drainage Improvements","estimate_number":"EST-2026-001","customer_name":"NCDOT","project_name":"Hwy 74 Drainage Phase 1","project_type":"Heavy civil","contract_type":"Lump sum","estimate_type":"Bid","bid_due_date":"2026-08-22","target_margin_percent":"14","default_overhead_percent":"8","default_contingency_percent":"5","notes":"Stormwater infrastructure replacement along Hwy 74 corridor.","status":"Draft Estimate"},
    {"estimate_name":"Apex Industrial Park Site Prep","estimate_number":"EST-2026-002","customer_name":"Apex Industrial LLC","project_name":"Industrial Park Phase 2","project_type":"Site development","contract_type":"Unit price","estimate_type":"Detailed","bid_due_date":"2026-09-05","target_margin_percent":"16","default_overhead_percent":"7","default_contingency_percent":"6","notes":"Site grading, utilities, and paving for 45-acre industrial park.","status":"Draft Estimate"},
    {"estimate_name":"Downtown Water Main Replacement","estimate_number":"EST-2026-003","customer_name":"City of Raleigh","project_name":"Water Main Phase 3","project_type":"Underground utilities","contract_type":"Lump sum","estimate_type":"Bid","bid_due_date":"2026-09-18","target_margin_percent":"13","default_overhead_percent":"9","default_contingency_percent":"5","notes":"16-inch water main replacement through downtown corridor.","status":"Submitted"},
    {"estimate_name":"I-40 Interchange Earthwork","estimate_number":"EST-2026-004","customer_name":"NCDOT","project_name":"I-40 Interchange Expansion","project_type":"Heavy civil","contract_type":"Unit price","estimate_type":"Bid","bid_due_date":"2026-10-01","target_margin_percent":"15","default_overhead_percent":"8","default_contingency_percent":"7","notes":"Mass earthwork and grading for I-40 interchange widening project.","status":"Awarded"},
    {"estimate_name":"Solar Farm Road & Pad Construction","estimate_number":"EST-2026-005","customer_name":"SunPath Energy","project_name":"Blue Ridge Solar Phase 1","project_type":"Grading","contract_type":"Cost plus","estimate_type":"Preliminary","bid_due_date":"2026-10-15","target_margin_percent":"18","default_overhead_percent":"6","default_contingency_percent":"8","notes":"Access roads, panel pads, and drainage for 200-acre solar installation.","status":"Draft Estimate"},
]

BID_PIPELINE = [
    {"bid_number":"BID-2026-001","customer_name":"NCDOT","stage":"Submitted","bid_amount":"2850000","probability_percent":"65","due_date":"2026-08-22","status":"active","notes":"Highway 74 drainage bid"},
    {"bid_number":"BID-2026-002","customer_name":"Apex Industrial LLC","stage":"Negotiation","bid_amount":"4200000","probability_percent":"80","due_date":"2026-09-05","status":"active","notes":"Industrial park site prep"},
    {"bid_number":"BID-2026-003","customer_name":"City of Raleigh","stage":"Awarded","bid_amount":"1950000","probability_percent":"100","due_date":"2026-09-18","status":"active","notes":"Water main replacement - AWARDED"},
]

print("Creating estimates...")
for est in ESTIMATES:
    s, b = post("/api/estimates", est, token)
    print(f"  {s}  {est['estimate_number']}  {est['estimate_name'][:40]}")

print("\nCreating bid pipeline...")
for bid in BID_PIPELINE:
    s, b = post("/api/estimator/bid-pipeline", bid, token)
    print(f"  {s}  {bid['bid_number']}  {bid['customer_name']}")

print("\nDone.")
