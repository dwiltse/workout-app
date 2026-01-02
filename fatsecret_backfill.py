import requests
from fatsecret import Fatsecret
import psycopg2
from datetime import datetime, timedelta
import os
import json

# --- CONFIGURATION ---
CONSUMER_KEY = 'c3ab1cd3b0cd4347baf73ba80f1d5f57'
CONSUMER_SECRET = 'd2f15ae45ad0489d83d763cf856ffab8'
TOKEN_CACHE_FILE = '.fatsecret_tokens.json'

def load_tokens():
    """Load saved access tokens."""
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, 'rb') as f:
            return pickle.load(f)
    return None

def get_fatsecret_client():
    """Initialize FatSecret client with cached tokens."""
    tokens = load_tokens()
    if tokens:
        print("Using saved authentication tokens...")
        fs = Fatsecret(
            CONSUMER_KEY, 
            CONSUMER_SECRET,
            session_token=(tokens['access_token'], tokens['access_token_secret'])
        )
        return fs
    else:
        print("Error: No cached tokens found. Run fatsecret_migration.py first to authenticate.")
        return None

def fetch_food_diary(fs, date_str):
    """Fetches food entries for a specific date."""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        diary = fs.food_entries_get(date=date_obj)
        return diary
    except Exception as e:
        print(f"  Error fetching {date_str}: {e}")
        return []

def save_to_neon(data, date_str, db_conn=None):
    """Saves the fetched data into Neon Postgres."""
    if db_conn is None:
        db_conn = "postgres://user:password@ep-xyz.aws.neon.tech/neondb?sslmode=require"
        
    conn = psycopg2.connect(db_conn)
    cur = conn.cursor()
    
    # Create table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diet_logs (
            id SERIAL PRIMARY KEY,
            date DATE,
            meal VARCHAR(50),
            food_name VARCHAR(255),
            calories DECIMAL,
            protein DECIMAL,
            carbs DECIMAL,
            fat DECIMAL,
            entry_id BIGINT UNIQUE
        );
    """)
    
    # Handle both old format (dict) and new format (list directly)
    if isinstance(data, list):
        entries = data
    else:
        entries = data.get('food_entries', {}).get('food_entry', [])
        if not isinstance(entries, list):
            entries = [entries] if entries else []
    
    inserted = 0
    skipped = 0
    
    for entry in entries:
        try:
            cur.execute("""
                INSERT INTO diet_logs (date, meal, food_name, calories, protein, carbs, fat, entry_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (entry_id) DO UPDATE SET
                    date = EXCLUDED.date,
                    meal = EXCLUDED.meal,
                    food_name = EXCLUDED.food_name,
                    calories = EXCLUDED.calories,
                    protein = EXCLUDED.protein,
                    carbs = EXCLUDED.carbs,
                    fat = EXCLUDED.fat;
            """, (
                date_str,
                entry.get('meal', 'Unknown'),
                entry.get('food_entry_name'),
                entry.get('calories'),
                entry.get('protein'),
                entry.get('carbohydrate'),
                entry.get('fat'),
                entry.get('food_entry_id')
            ))
            # Check if the row was inserted (not skipped due to conflict)
            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  Error inserting entry for {date_str}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    return inserted, skipped

if __name__ == "__main__":
    try:
        db_conn = input("Enter your Neon DB Connection String: ").strip()
        
        print("--- Starting 7-Day FatSecret Backfill ---")
        fs = get_fatsecret_client()
        
        if fs is None:
            exit(1)
        
        # Get last 7 days (including today)
        today = datetime.now()
        dates_to_fetch = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7, -1, -1)]
        
        total_inserted = 0
        total_skipped = 0
        
        print(f"\nFetching data for {len(dates_to_fetch)} days ({dates_to_fetch[0]} to {dates_to_fetch[-1]})...\n")
        
        for date_str in dates_to_fetch:
            print(f"Processing {date_str}...", end=" ")
            data = fetch_food_diary(fs, date_str)
            inserted, skipped = save_to_neon(data, date_str, db_conn)
            total_inserted += inserted
            total_skipped += skipped
            print(f"({inserted} new, {skipped} duplicates)")
        
        print(f"\n✓ Backfill complete!")
        print(f"  Total inserted: {total_inserted}")
        print(f"  Total skipped (duplicates): {total_skipped}")
        
    except Exception as e:
        print(f"\nError: {e}")
