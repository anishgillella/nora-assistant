
import requests
import sys

BASE_URL = "http://localhost:8000/api"

def reset_database():
    print("🗑️  Wiping Database...")
    
    # 1. Clear Browsing History
    try:
        r = requests.delete(f"{BASE_URL}/memory/clear")
        if r.status_code == 200:
            print("✅ Browsing Memory Cleared")
        else:
            print(f"❌ Failed to clear browsing memory: {r.text}")
    except Exception as e:
        print(f"❌ Error connecting to backend: {e}")
        return

    # 2. Clear Product Catalog
    try:
        r = requests.delete(f"{BASE_URL}/recommendations/clear")
        if r.status_code == 200:
            print("✅ Product Catalog Cleared")
        else:
            print(f"❌ Failed to clear product catalog: {r.text}")
    except Exception as e:
         print(f"❌ Error connecting to backend: {e}")

    print("\n✨ Database is now empty. Verification Verification Script or frontend browsing will now ingest RICH data.")

if __name__ == "__main__":
    reset_database()
