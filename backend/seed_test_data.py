"""Script đẩy dữ liệu test lên Supabase."""
import urllib.request, json, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY  = os.getenv("SUPABASE_JWT_SECRET")  # service_role key

HEADERS = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

def call(method, path, body=None):
    url  = SUPABASE_URL + "/rest/v1/" + path
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

print("=== 1. INSERT USER ===")
status, resp = call("POST", "users", {
    "user_id": USER_ID,
    "email": "testuser@smartlearning.dev",
    "display_name": "Test User Smart Learning",
})
print(f"Status: {status}")
print(json.dumps(resp, indent=2, ensure_ascii=False))

print("\n=== 2. INSERT TASK ===")
status, resp = call("POST", "tasks", {
    "user_id": USER_ID,
    "title": "Học FastAPI & Supabase",
    "description": "Test đẩy dữ liệu lên Supabase từ backend",
    "status": "todo",
    "priority": 1,
    "subject_name": "Backend Development",
})
print(f"Status: {status}")
print(json.dumps(resp, indent=2, ensure_ascii=False))

print("\n=== 3. READ TASKS ===")
status, resp = call("GET", "tasks?select=task_id,title,status,created_at&limit=5")
print(f"Status: {status}")
print(json.dumps(resp, indent=2, ensure_ascii=False))

print("\n=== 4. READ USERS ===")
status, resp = call("GET", "users?select=user_id,email,display_name&limit=5")
print(f"Status: {status}")
print(json.dumps(resp, indent=2, ensure_ascii=False))
