import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load .env từ thư mục backend/, bất kể chạy từ đâu
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_env_path)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def test_supabase_connection():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Missing SUPABASE_URL or SUPABASE_KEY in environment.")
        return False
    # Try to list tables (rest/v1) as a simple test
    url = f"{SUPABASE_URL}/rest/v1/"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            print("Supabase connection OK. Response:", resp.text[:200])
            return True
        else:
            print(f"Supabase connection failed. Status: {resp.status_code}, Body: {resp.text}")
            return False
    except Exception as e:
        print("Supabase connection error:", e)
        return False

if __name__ == "__main__":
    test_supabase_connection()