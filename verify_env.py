import os
from dotenv import load_dotenv

print("--- Loading .env ---")
load_dotenv()

print("\n--- Environment Variables Check ---")
keys = [k for k in os.environ.keys() if 'OPENROUTER' in k.upper()]

if not keys:
    print("❌ No OPENROUTER keys found in environment.")
else:
    for k in keys:
        val = os.environ[k]
        masked = val[:5] + "..." if len(val) > 5 else "EMPTY"
        print(f"✅ Found {k}: {masked}")

target = os.getenv('OPENROUTER_API_KEY')
print(f"\nTarget 'OPENROUTER_API_KEY' loaded? : {bool(target)}")
