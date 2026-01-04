#!/usr/bin/env python3
"""
Debug Fitbit OAuth Issues
Simple script to test Fitbit authorization step by step
"""

import os
import requests
from urllib.parse import urlencode

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv('.env')
except ImportError:
    pass

# Get credentials
CLIENT_ID = os.environ.get('FITBIT_CLIENT_ID')
CLIENT_SECRET = os.environ.get('FITBIT_CLIENT_SECRET')

print("=== Fitbit OAuth Debug ===\n")

print(f"Client ID: {CLIENT_ID}")
print(f"Client Secret: {'*' * 20 if CLIENT_SECRET else 'NOT FOUND'}")
print()

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Missing credentials in .env.local")
    exit(1)

# Test 1: Simple authorization URL (minimal scope)
print("🧪 Test 1: Basic authorization URL")
params = {
    'response_type': 'code',
    'client_id': CLIENT_ID,
    'redirect_uri': 'http://127.0.0.1:8080/',
    'scope': 'activity'  # Just basic scope
}

auth_url = f"https://www.fitbit.com/oauth2/authorize?{urlencode(params)}"
print(f"URL: {auth_url}")

# Test the URL with a HEAD request
print("\n🌐 Testing URL accessibility...")
try:
    response = requests.head(auth_url, allow_redirects=True)
    print(f"Status: {response.status_code}")
    print(f"Final URL: {response.url}")

    if response.status_code == 200:
        print("✅ URL is accessible")
    elif response.status_code == 403:
        print("❌ 403 Forbidden - App configuration issue")
    else:
        print(f"⚠️ Unexpected status: {response.status_code}")

except Exception as e:
    print(f"❌ Error: {e}")

print(f"\n📋 Manual test:")
print(f"Copy this URL and paste it in your browser:")
print(f"{auth_url}")
print(f"\nIf you get 403, the issue is with your Fitbit app settings.")
print(f"If it works, the issue is with our Python script.")