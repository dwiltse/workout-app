#!/usr/bin/env python3
"""
Test script to explore what data FatSecret API returns for user profile.
This will help determine if calorie goals are available via the API.
"""

import json
import os
from fatsecret import Fatsecret

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv('.env')
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables...")

# FatSecret credentials
CONSUMER_KEY = os.environ.get('FATSECRET_CLIENT_ID')
CONSUMER_SECRET = os.environ.get('FATSECRET_CLIENT_SECRET')
TOKEN_CACHE_FILE = '.fatsecret_tokens.json'

def test_profile_data():
    """Test what profile data is available from FatSecret API."""

    # Validate credentials
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        print("❌ Missing FatSecret credentials!")
        print("Set FATSECRET_CLIENT_ID and FATSECRET_CLIENT_SECRET in .env.local")
        return

    # Load saved tokens
    if not os.path.exists(TOKEN_CACHE_FILE):
        print("❌ No cached tokens found!")
        print("Run fatsecret_migration.py first to authenticate")
        return

    with open(TOKEN_CACHE_FILE, 'r') as f:
        tokens = json.load(f)

    print("🔑 Using cached tokens...")

    # Initialize FatSecret client
    fs = Fatsecret(
        CONSUMER_KEY,
        CONSUMER_SECRET,
        session_token=(tokens['access_token'], tokens['access_token_secret'])
    )

    print("\n🔍 Testing available profile methods...\n")

    # Test 1: profile_get()
    try:
        print("📊 Testing profile_get()...")
        profile_data = fs.profile_get()
        print("✅ SUCCESS - Profile data found:")
        print(json.dumps(profile_data, indent=2))
        print()
    except Exception as e:
        print(f"❌ profile_get() failed: {e}")
        print()

    # Test 2: Check what methods are available
    print("📋 Available methods on FatSecret client:")
    methods = [method for method in dir(fs) if not method.startswith('_')]
    for method in sorted(methods):
        if 'profile' in method.lower() or 'goal' in method.lower() or 'target' in method.lower():
            print(f"  🎯 {method}")
        elif method.endswith('_get') or method.endswith('_create'):
            print(f"  📄 {method}")

    print(f"\n📈 Total methods available: {len(methods)}")

    # Test 3: Try a recent food diary entry to see data structure
    try:
        print("\n🍎 Testing food_entries_get() for data structure reference...")
        from datetime import datetime, timedelta
        yesterday = datetime.now() - timedelta(days=1)
        recent_entries = fs.food_entries_get(date=yesterday)

        if recent_entries and len(recent_entries) > 0:
            print("✅ Sample food entry structure:")
            sample_entry = recent_entries[0] if isinstance(recent_entries, list) else recent_entries
            print(json.dumps(sample_entry, indent=2)[:500] + "..." if len(str(sample_entry)) > 500 else json.dumps(sample_entry, indent=2))
        else:
            print("ℹ️  No food entries found for yesterday")

    except Exception as e:
        print(f"❌ food_entries_get() failed: {e}")

if __name__ == "__main__":
    print("🔬 FatSecret API Profile Data Explorer")
    print("=" * 50)
    test_profile_data()
    print("\n✨ Profile exploration complete!")