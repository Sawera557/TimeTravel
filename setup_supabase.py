#!/usr/bin/env python3
"""
Supabase Database Setup Helper
This script helps verify and initialize your Supabase database schema
"""

import os
import sys
from supabase import create_client, Client
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')

def connect_to_supabase() -> Client | None:
    """Connect to Supabase and return client"""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        print("❌ Supabase credentials not found in .env file")
        print("   Please set SUPABASE_URL and SUPABASE_ANON_KEY")
        return None

    try:
        client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        print(f"✓ Connected to Supabase: {SUPABASE_URL}")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return None

def check_tables(client: Client) -> dict:
    """Check if required tables exist"""
    required_tables = ['tasks', 'snapshots', 'workspace_state']
    table_status = {}

    print("\n📋 Checking for required tables...")
    for table_name in required_tables:
        try:
            response = client.table(table_name).select('*', count='exact').limit(1).execute()
            table_status[table_name] = True
            count = response.count if hasattr(response, 'count') else 0
            print(f"   ✓ Table '{table_name}' exists ({count} rows)")
        except Exception as e:
            table_status[table_name] = False
            print(f"   ❌ Table '{table_name}' not found")

    return table_status

def check_initial_data(client: Client) -> bool:
    """Check if initial workspace state exists"""
    try:
        print("\n📊 Checking initial data...")
        workspace_response = client.table('workspace_state').select('*').eq(
            'id', '00000000-0000-0000-0000-000000000000'
        ).execute()

        if workspace_response.data:
            print("   ✓ Initial workspace state exists")
            return True
        else:
            print("   ⚠ Initial workspace state not found")
            return False
    except Exception as e:
        print(f"   ❌ Error checking workspace state: {e}")
        return False

def print_setup_instructions():
    """Print instructions for manual setup"""
    print("\n" + "="*60)
    print("SETUP INSTRUCTIONS")
    print("="*60)
    print("\n1. Go to Supabase SQL Editor:")
    print("   https://app.supabase.com/ → SQL Editor")
    print("\n2. Create a new query and copy the following SQL:")
    print("   File: supabase_schema_updated.sql")
    print("\n3. Run the SQL query")
    print("\n4. Return here and run this script again to verify")
    print("\nAlternatively, follow detailed instructions in SUPABASE_SETUP.md")
    print("="*60 + "\n")

def main():
    """Main execution"""
    print("🚀 Supabase Database Setup Helper\n")

    # Connect to Supabase
    client = connect_to_supabase()
    if not client:
        print_setup_instructions()
        sys.exit(1)

    # Check tables
    table_status = check_tables(client)
    all_tables_exist = all(table_status.values())

    if all_tables_exist:
        print("\n✅ All required tables exist!")
        check_initial_data(client)
        print("\n🎉 Your Supabase database is properly configured!")
        print("   You can now start your Flask application:")
        print("   $ python app.py")
        sys.exit(0)
    else:
        print("\n❌ Some tables are missing")
        print_setup_instructions()
        sys.exit(1)

if __name__ == '__main__':
    main()

