#!/usr/bin/env python3
"""Quick test to verify Supabase connection."""

import os
import sys
from supabase import create_client, Client

# Load .env manually
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env_file()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')

print("=" * 60)
print("SUPABASE CONNECTION TEST")
print("=" * 60)

# Check environment variables
print(f"\n1. Environment Variables:")
print(f"   SUPABASE_URL: {'✓ Found' if SUPABASE_URL else '✗ Missing'}")
print(f"   SUPABASE_ANON_KEY: {'✓ Found' if SUPABASE_ANON_KEY else '✗ Missing'}")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    print("\n✗ Missing credentials!")
    sys.exit(1)

# Test connection
print(f"\n2. Testing Connection...")
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    print("   ✓ Client initialized")

    # Try to access workspace_state table
    result = supabase.table('workspace_state').select('*').limit(1).execute()
    print(f"   ✓ Connected to Supabase")
    print(f"   ✓ workspace_state table accessible")

    print("\n✓ SUCCESS: Supabase is configured correctly!")
    print("\n" + "=" * 60)

except Exception as e:
    print(f"   ✗ Connection failed: {e}")
    print("\n✗ FAILURE: Check your Supabase credentials")
    print("=" * 60)
    sys.exit(1)

