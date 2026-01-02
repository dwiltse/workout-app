#!/usr/bin/env python
"""
Non-interactive weight import for weekly automation.
Auto-backfills 3 months and skips duplicates.
Can be run via cron or Task Scheduler.
"""

import requests
from fatsecret import Fatsecret
import psycopg2
from datetime import datetime, timedelta
import os
import json
import sys

# --- CONFIGURATION ---
CONSUMER_KEY = 'c3ab1cd3b0cd4347baf73ba80f1d5f57'
CONSUMER_SECRET = 'd2f15ae45ad0489d83d763cf856ffab8'
TOKEN_CACHE_FILE = '.fatsecret_tokens.json'

# Get DB connection from environment or use default
DB_CONNECTION_STRING = os.getenv(
    'FATSECRET_DB_CONNECTION',
    "postgres://user:password@ep-xyz.aws.neon.tech/neondb?sslmode=require"
)

# Default to current month
TARGET_DATE = datetime.now().strftime('%Y-%m-%d')
# ---------------------

def load_tokens():
    """Load saved access tokens."""
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

def get_fatsecret_client():
    """Initialize FatSecret client with cached tokens."""
    tokens = load_tokens()
    if tokens:
        fs = Fatsecret(
            CONSUMER_KEY, 
            CONSUMER_SECRET,
            session_token=(tokens['access_token'], tokens['access_token_secret'])
        )
        return fs
    else:
        print("Error: No cached tokens found. Run fatsecret_migration.py first to authenticate.")
        return None

def fetch_weight_data(fs, date_str):
    """
    Fetches weight entries for a specific month.
    date_str should be in YYYY-MM-DD format (any day in the desired month)
    """
    try:
        # Convert string date to datetime object
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        # The library fetches all weights for the month
        weights = fs.weights_get_month(date=date_obj)
        return weights
    except KeyError:
        # No weight entries for that month
        return []
    except Exception as e:
        print(f"Error fetching weight data for {date_str}: {e}")
        return []

def save_to_neon(data, db_conn):
    """
    Saves the fetched weight data into Neon Postgres.
    """
    conn = psycopg2.connect(db_conn)
    cur = conn.cursor()
    
    # Create table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weight_logs (
            id SERIAL PRIMARY KEY,
            date DATE,
            weight DECIMAL(5,1),
            fat_percentage DECIMAL(5,2),
            comment TEXT,
            entry_id BIGINT UNIQUE
        );
    """)
    
    # Handle both old format (dict) and new format (list directly)
    if isinstance(data, list):
        entries = data
    else:
        entries = data.get('weight_entries', {}).get('weight_entry', [])
        if not isinstance(entries, list):
            entries = [entries] if entries else []
    
    inserted = 0
    skipped = 0
    
    for entry in entries:
        try:
            # Extract weight entry fields
            # FatSecret returns: date_int (days since epoch), weight_kg
            date_int = entry.get('date_int')
            weight_kg = entry.get('weight_kg')
            fat_pct = entry.get('fat')
            comment = entry.get('comment', '')
            entry_id = entry.get('weight_entry_id', date_int)  # Use date_int as fallback ID
            
            # Convert date_int (days since epoch) to date
            if date_int:
                date_val = (datetime(1970, 1, 1) + timedelta(days=int(date_int))).date()
            else:
                date_val = None
            
            # Convert kg to lbs (1 kg = 2.20462 lbs)
            weight_lbs = float(weight_kg) * 2.20462 if weight_kg else None
            
            cur.execute("""
                INSERT INTO weight_logs (date, weight, fat_percentage, comment, entry_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (entry_id) DO UPDATE SET
                    date = EXCLUDED.date,
                    weight = EXCLUDED.weight,
                    fat_percentage = EXCLUDED.fat_percentage,
                    comment = EXCLUDED.comment;
            """, (date_val, weight_lbs, fat_pct, comment, entry_id))
            
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"Error inserting weight entry: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    return inserted, skipped

def main():
    """Main function - auto-backfill 3 months."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting FatSecret Weight Backfill...")
    
    fs = get_fatsecret_client()
    if fs is None:
        print("Failed to authenticate. Exiting.")
        sys.exit(1)
    
    total_inserted = 0
    total_skipped = 0
    
    # Backfill last 3 months
    base_date = datetime.now()
    for i in range(3):
        check_date = (base_date - timedelta(days=30*i)).strftime('%Y-%m-%d')
        data = fetch_weight_data(fs, check_date)
        inserted, skipped = save_to_neon(data, DB_CONNECTION_STRING)
        total_inserted += inserted
        total_skipped += skipped
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Complete!")
    print(f"  Inserted: {total_inserted}")
    print(f"  Duplicates skipped: {total_skipped}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
