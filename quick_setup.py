#!/usr/bin/env python3
"""
Quick Supabase Setup for TimeTravel Tasks
Helps verify and troubleshoot Supabase integration
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def print_section(text):
    """Print a formatted section"""
    print(f"\n{'─'*60}")
    print(f"  {text}")
    print(f"{'─'*60}\n")

def check_env_file():
    """Check if .env file exists and has required variables"""
    print_section("1️⃣  Checking Environment Configuration")

    env_path = Path('.env')

    if not env_path.exists():
        print("❌ .env file not found!")
        print("\n   Create it with:")
        print("   - Right-click in VS Code Explorer")
        print("   - Select 'New File'")
        print("   - Name it '.env'")
        print("\n   Or use PowerShell:")
        print("   New-Item -Name '.env' -ItemType File")
        return False

    print("✓ .env file found")

    # Load and check for required variables
    load_dotenv()

    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')

    if not url:
        print("❌ SUPABASE_URL not set in .env")
        return False
    print(f"✓ SUPABASE_URL: {url[:30]}...")

    if not key:
        print("❌ SUPABASE_ANON_KEY not set in .env")
        return False
    print(f"✓ SUPABASE_ANON_KEY: {key[:20]}...")

    return True

def check_dependencies():
    """Check if required Python packages are installed"""
    print_section("2️⃣  Checking Python Dependencies")

    required = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'supabase': 'Supabase',
        'dotenv': 'python-dotenv'
    }

    all_installed = True
    for module, package_name in required.items():
        try:
            __import__(module)
            print(f"✓ {package_name} installed")
        except ImportError:
            print(f"❌ {package_name} NOT installed")
            print(f"   Install with: pip install {package_name}")
            all_installed = False

    return all_installed

def check_supabase_connection():
    """Try to connect to Supabase"""
    print_section("3️⃣  Checking Supabase Connection")

    try:
        from supabase import create_client
    except ImportError:
        print("❌ Supabase SDK not installed")
        print("   Run: pip install supabase")
        return False

    try:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')

        if not url or not key:
            print("❌ Credentials not set")
            return False

        client = create_client(url, key)
        print(f"✓ Connected to: {url}")
        return client
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def check_database_tables(client):
    """Check if required tables exist"""
    print_section("4️⃣  Checking Database Tables")

    if not client:
        print("⚠ Skipping (Supabase not connected)")
        return False

    tables = {'tasks': '📋', 'snapshots': '📸', 'workspace_state': '🏢'}
    all_exist = True

    for table_name, emoji in tables.items():
        try:
            response = client.table(table_name).select('*', count='exact').limit(1).execute()
            count = getattr(response, 'count', 0)
            print(f"✓ {emoji} {table_name:20} ({count} rows)")
        except Exception as e:
            error_msg = str(e)
            if 'PGRST205' in error_msg or 'Could not find the table' in error_msg:
                print(f"❌ {emoji} {table_name:20} - TABLE NOT FOUND")
                print(f"   Action: Run SQL schema in Supabase SQL Editor")
            else:
                print(f"❌ {emoji} {table_name:20} - Error: {error_msg[:40]}")
            all_exist = False

    return all_exist

def print_next_steps(tables_exist):
    """Print next steps based on current status"""
    print_section("📋 Next Steps")

    if not tables_exist:
        print("1. Go to Supabase SQL Editor:")
        print("   https://app.supabase.com/project/txsrejfrqlhrheqcsmzp")
        print("\n2. Create a new query")
        print("\n3. Copy and paste 'supabase_schema_updated.sql'")
        print("\n4. Click 'Run'")
        print("\n5. Run this script again to verify")
    else:
        print("✅ All setup looks good!")
        print("\nYou can now:")
        print("  • Start Flask: python app.py")
        print("  • Test app:   http://localhost:5000")
        print("  • Check health: http://localhost:5000/health")
        print("  • Diagnostics: http://localhost:5000/api/diagnostic")

def print_help():
    """Print help information"""
    print_header("❓ HELP - Common Issues")

    print("Issue: 'Could not find the table PGRST205'")
    print("  Solution: Run SQL schema in Supabase SQL Editor\n")

    print("Issue: 'SUPABASE_URL not set'")
    print("  Solution: Create .env file with credentials\n")

    print("Issue: 'Connection failed'")
    print("  Solution: Check internet, verify credentials, check project is not paused\n")

def main():
    """Run full setup check"""
    print_header("🚀 Supabase Integration Check")

    # Step 1: Check .env
    env_ok = check_env_file()
    if not env_ok:
        print_help()
        return False

    # Step 2: Check dependencies
    deps_ok = check_dependencies()
    if not deps_ok:
        print("\n⚠ Missing dependencies! Install them first.")
        print("  Run: pip install -r requirements.txt")
        return False

    # Step 3: Check Supabase connection
    client = check_supabase_connection()
    if not client:
        print("\n⚠ Could not connect to Supabase")
        print_help()
        return False

    # Step 4: Check tables
    tables_exist = check_database_tables(client)

    # Print next steps
    print_next_steps(tables_exist)

    print_header("✅ Check Complete" if tables_exist else "⚠ Setup Required")

    return tables_exist

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

