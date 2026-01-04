import requests
from fatsecret import Fatsecret
import psycopg2
from datetime import datetime, timedelta
import os
import json

# Load environment variables from .env files
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv('.env')
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Falling back to system environment variables...")

# --- CONFIGURATION ---
# FatSecret Credentials
CONSUMER_KEY = os.environ.get('FATSECRET_CLIENT_ID')
CONSUMER_SECRET = os.environ.get('FATSECRET_CLIENT_SECRET')
TOKEN_CACHE_FILE = '.fatsecret_tokens.json'

# Validate required environment variables
if not CONSUMER_KEY or not CONSUMER_SECRET:
    print("\n⚠️  Missing FatSecret credentials!")
    print("Set environment variables: FATSECRET_CLIENT_ID and FATSECRET_CLIENT_SECRET")
    print("Or add them to your .env.local file")
    exit(1)

# 3. Date to fetch (YYYY-MM-DD) - Yesterday
TARGET_DATE = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
# ---------------------

def save_tokens(fs):
    """Save access tokens to file for reuse."""
    tokens = {
        'access_token': fs.access_token,
        'access_token_secret': fs.access_token_secret
    }
    with open(TOKEN_CACHE_FILE, 'w') as f:
        json.dump(tokens, f)
    print(f"Tokens saved to {TOKEN_CACHE_FILE}")

def load_tokens():
    """Load saved access tokens."""
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

def get_fatsecret_client():
    """
    Initialize and authenticate the FatSecret API client.
    """
    # Try to load cached tokens first
    tokens = load_tokens()
    if tokens:
        print("Using saved authentication tokens...")
        # Pass tokens as session_token tuple to the constructor
        fs = Fatsecret(
            CONSUMER_KEY, 
            CONSUMER_SECRET,
            session_token=(tokens['access_token'], tokens['access_token_secret'])
        )
        return fs
    
    # Otherwise, perform 3-legged OAuth
    fs = Fatsecret(CONSUMER_KEY, CONSUMER_SECRET)
    print("\n--- FatSecret OAuth 1.0 Authentication ---")
    
    # Step 1: Get authorization URL
    authorize_url = fs.get_authorize_url()
    print(f"\n1. Please visit this URL to authorize:\n{authorize_url}")
    
    try:
        import webbrowser
        webbrowser.open(authorize_url)
    except:
        pass
    
    # Step 2: Get verifier
    verifier = input("\n2. After authorizing, copy the verification code shown and paste it here: ").strip()
    
    # Step 3: Authenticate with verifier
    fs.authenticate(verifier)
    print("Authentication successful!")
    
    # Save tokens for future use
    save_tokens(fs)
    
    return fs

def fetch_food_diary(fs, date_str):
    """
    Fetches food entries for a specific date.
    date_str should be in YYYY-MM-DD format
    """
    print(f"Fetching food diary for {date_str}...")
    try:
        # Convert string date to datetime object
        # The library expects a datetime object and converts it internally to days since epoch
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        diary = fs.food_entries_get(date=date_obj)
        print(f"Successfully fetched diary")
        return diary
    except Exception as e:
        print(f"Error fetching diary: {e}")
        print(f"This might mean there are no entries for {date_str}, or there's a library issue")
        # Return empty structure
        return {'food_entries': {'food_entry': []}}

def save_to_neon(data, db_conn=None):
    """
    Saves the fetched data into Neon Postgres.
    """
    if db_conn is None:
        # Database connection is now handled in main()
        
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
    
    # Handle both old format (dict with 'food_entries' key) and new format (list directly)
    if isinstance(data, list):
        entries = data
    else:
        entries = data.get('food_entries', {}).get('food_entry', [])
        if not isinstance(entries, list):
            entries = [entries] if entries else []
        
    print(f"\nFound {len(entries)} entries. Inserting into DB...")
    
    for entry in entries:
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
            TARGET_DATE,
            entry.get('meal', 'Unknown'),
            entry.get('food_entry_name'),
            entry.get('calories'),
            entry.get('protein'),
            entry.get('carbohydrate'),
            entry.get('fat'),
            entry.get('food_entry_id')
        ))
    
    conn.commit()
    cur.close()
    conn.close()
    print("Success! Data saved to Neon.")

if __name__ == "__main__":
    try:
        # Database connection
        db_conn = os.environ.get('NEON_DB_URL') or os.environ.get('DATABASE_URL')
        if not db_conn:
            db_conn = input("Enter your Neon DB Connection String: ").strip()

        if not db_conn or "user:password" in db_conn:
            print("Please provide a valid Neon database connection string")
            print("You can set NEON_DB_URL or DATABASE_URL environment variable")
            exit(1)

        print("--- Starting FatSecret API Export ---")
        fs = get_fatsecret_client()
        
        # Allow user to choose date
        date_input = input(f"\nEnter date to fetch (YYYY-MM-DD) [default: {TARGET_DATE}]: ").strip()
        fetch_date = date_input if date_input else TARGET_DATE
        
        data = fetch_food_diary(fs, fetch_date)
        save_to_neon(data, db_conn)
        
    except Exception as e:
        print(f"\nError: {e}")
