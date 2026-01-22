#!/usr/bin/env python3
"""
FatSecret Nutrition Data Sync Tool

Syncs nutrition data from FatSecret API to Neon Postgres database.
Supports both single-date fetching and multi-day backfill operations.

Usage:
    # Interactive mode (prompts for date)
    python fatsecret_sync.py

    # Fetch specific date
    python fatsecret_sync.py --date 2024-01-15

    # Backfill last 7 days
    python fatsecret_sync.py --backfill 7

    # Backfill last 30 days (quiet mode for cron)
    python fatsecret_sync.py --backfill 30 --quiet

    # Initial OAuth authentication
    python fatsecret_sync.py --auth

Environment Variables:
    FATSECRET_CLIENT_ID          - FatSecret API consumer key
    FATSECRET_CLIENT_SECRET      - FatSecret API consumer secret
    FATSECRET_ACCESS_TOKEN       - OAuth access token (optional, for CI/cron)
    FATSECRET_ACCESS_TOKEN_SECRET - OAuth access token secret (optional, for CI/cron)
    FATSECRET_TOKEN_CACHE        - Token cache file path (default: .fatsecret_tokens.json)
    NEON_DB_URL                  - Neon Postgres connection string
    DATABASE_URL                 - Alternative database connection string
"""

import argparse
import sys
import os
import json
import webbrowser
from datetime import datetime, timedelta
from fatsecret import Fatsecret
import psycopg2

# Load environment variables from .env files
try:
    from dotenv import load_dotenv
    load_dotenv('.env.local')
    load_dotenv('.env')
except ImportError:
    pass  # python-dotenv is optional

# --- CONFIGURATION ---
CONSUMER_KEY = os.environ.get('FATSECRET_CLIENT_ID')
CONSUMER_SECRET = os.environ.get('FATSECRET_CLIENT_SECRET')
TOKEN_CACHE_FILE = os.environ.get('FATSECRET_TOKEN_CACHE', '.fatsecret_tokens.json')

# Optional: Pre-configured tokens for CI/cron environments
ENV_ACCESS_TOKEN = os.environ.get('FATSECRET_ACCESS_TOKEN')
ENV_ACCESS_TOKEN_SECRET = os.environ.get('FATSECRET_ACCESS_TOKEN_SECRET')

class QuietMode:
    """Context manager for suppressing print statements in quiet mode."""
    def __init__(self, quiet=False):
        self.quiet = quiet
        self.original_stdout = None

    def __enter__(self):
        if self.quiet:
            self.original_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
        return self

    def __exit__(self, *args):
        if self.quiet and self.original_stdout:
            sys.stdout.close()
            sys.stdout = self.original_stdout

def validate_credentials():
    """Validate that required credentials are present."""
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        print("\n⚠️  Missing FatSecret credentials!")
        print("Set environment variables: FATSECRET_CLIENT_ID and FATSECRET_CLIENT_SECRET")
        print("Or add them to your .env.local file")
        sys.exit(1)

def save_tokens(fs):
    """Save access tokens to file for reuse."""
    tokens = {
        'access_token': fs.access_token,
        'access_token_secret': fs.access_token_secret
    }
    with open(TOKEN_CACHE_FILE, 'w') as f:
        json.dump(tokens, f)
    print(f"✓ Tokens saved to {TOKEN_CACHE_FILE}")

def load_tokens():
    """Load saved access tokens from file or environment variables."""
    # First try environment variables (for CI/cron)
    if ENV_ACCESS_TOKEN and ENV_ACCESS_TOKEN_SECRET:
        return {
            'access_token': ENV_ACCESS_TOKEN,
            'access_token_secret': ENV_ACCESS_TOKEN_SECRET
        }

    # Fall back to file cache
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, 'r') as f:
            return json.load(f)

    return None

def get_fatsecret_client(force_auth=False):
    """
    Initialize and authenticate the FatSecret API client.

    Args:
        force_auth: If True, force new OAuth authentication flow

    Returns:
        Fatsecret client instance or None on failure
    """
    # Try to load cached tokens first (unless forcing new auth)
    if not force_auth:
        tokens = load_tokens()
        if tokens:
            print("✓ Using saved authentication tokens")
            try:
                fs = Fatsecret(
                    CONSUMER_KEY,
                    CONSUMER_SECRET,
                    session_token=(tokens['access_token'], tokens['access_token_secret'])
                )
                return fs
            except Exception as e:
                print(f"⚠️  Cached tokens invalid: {e}")
                print("Starting new authentication flow...")

    # Perform 3-legged OAuth
    fs = Fatsecret(CONSUMER_KEY, CONSUMER_SECRET)
    print("\n--- FatSecret OAuth 1.0 Authentication ---")

    # Step 1: Get authorization URL
    authorize_url = fs.get_authorize_url()
    print(f"\n1. Please visit this URL to authorize:\n{authorize_url}")

    try:
        webbrowser.open(authorize_url)
    except Exception:
        pass  # Browser open is optional, continue silently

    # Step 2: Get verifier
    verifier = input("\n2. After authorizing, copy the verification code shown and paste it here: ").strip()

    if not verifier:
        print("⚠️  No verification code provided")
        return None

    # Step 3: Authenticate with verifier
    try:
        fs.authenticate(verifier)
        print("✓ Authentication successful!")

        # Save tokens for future use
        save_tokens(fs)

        return fs
    except Exception as e:
        print(f"⚠️  Authentication failed: {e}")
        return None

def fetch_food_diary(fs, date_str):
    """
    Fetches food entries for a specific date.

    Args:
        fs: Fatsecret client instance
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Food diary data (dict or list)
    """
    try:
        # Convert string date to datetime object
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        diary = fs.food_entries_get(date=date_obj)
        return diary
    except Exception as e:
        print(f"  ⚠️  Error fetching {date_str}: {e}")
        # Return empty structure to continue processing other dates
        return {'food_entries': {'food_entry': []}}

def save_to_neon(data, date_str, db_conn, quiet=False):
    """
    Saves the fetched data into Neon Postgres.

    Args:
        data: Food diary data from FatSecret API
        date_str: Date string in YYYY-MM-DD format
        db_conn: Database connection string
        quiet: If True, suppress progress output

    Returns:
        Tuple of (inserted_count, updated_count)
    """
    try:
        with psycopg2.connect(db_conn) as conn:
            with conn.cursor() as cur:
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
                        fiber DECIMAL,
                        sugar DECIMAL,
                        sodium DECIMAL,
                        saturated_fat DECIMAL,
                        polyunsaturated_fat DECIMAL,
                        monounsaturated_fat DECIMAL,
                        cholesterol DECIMAL,
                        potassium DECIMAL,
                        entry_id BIGINT UNIQUE
                    );
                """)

                # Add new columns if they don't exist (for existing tables)
                new_columns = ['sugar', 'sodium', 'saturated_fat', 'polyunsaturated_fat',
                               'monounsaturated_fat', 'cholesterol', 'potassium']
                for column in new_columns:
                    cur.execute(f"""
                        DO $$
                        BEGIN
                            ALTER TABLE diet_logs ADD COLUMN {column} DECIMAL;
                        EXCEPTION
                            WHEN duplicate_column THEN NULL;
                        END $$;
                    """)

                # Handle both old format (dict with 'food_entries' key) and new format (list directly)
                if isinstance(data, list):
                    entries = data
                else:
                    entries = data.get('food_entries', {}).get('food_entry', [])
                    if not isinstance(entries, list):
                        entries = [entries] if entries else []

                if not quiet:
                    print(f"  Found {len(entries)} entries", end="")

                inserted_count = 0
                updated_count = 0

                for entry in entries:
                    # Store current count to detect if this is insert or update
                    cur.execute("SELECT COUNT(*) FROM diet_logs WHERE entry_id = %s",
                               (entry.get('food_entry_id'),))
                    exists_before = cur.fetchone()[0] > 0

                    cur.execute("""
                        INSERT INTO diet_logs (date, meal, food_name, calories, protein, carbs, fat, fiber,
                                               sugar, sodium, saturated_fat, polyunsaturated_fat, monounsaturated_fat,
                                               cholesterol, potassium, entry_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (entry_id) DO UPDATE SET
                            date = EXCLUDED.date,
                            meal = EXCLUDED.meal,
                            food_name = EXCLUDED.food_name,
                            calories = EXCLUDED.calories,
                            protein = EXCLUDED.protein,
                            carbs = EXCLUDED.carbs,
                            fat = EXCLUDED.fat,
                            fiber = EXCLUDED.fiber,
                            sugar = EXCLUDED.sugar,
                            sodium = EXCLUDED.sodium,
                            saturated_fat = EXCLUDED.saturated_fat,
                            polyunsaturated_fat = EXCLUDED.polyunsaturated_fat,
                            monounsaturated_fat = EXCLUDED.monounsaturated_fat,
                            cholesterol = EXCLUDED.cholesterol,
                            potassium = EXCLUDED.potassium;
                    """, (
                        date_str,
                        entry.get('meal', 'Unknown'),
                        entry.get('food_entry_name'),
                        entry.get('calories'),
                        entry.get('protein'),
                        entry.get('carbohydrate'),
                        entry.get('fat'),
                        entry.get('fiber'),
                        entry.get('sugar'),
                        entry.get('sodium'),
                        entry.get('saturated_fat'),
                        entry.get('polyunsaturated_fat'),
                        entry.get('monounsaturated_fat'),
                        entry.get('cholesterol'),
                        entry.get('potassium'),
                        entry.get('food_entry_id')
                    ))

                    if exists_before:
                        updated_count += 1
                    else:
                        inserted_count += 1

                conn.commit()

                if not quiet:
                    print(f" → {inserted_count} inserted, {updated_count} updated")

                return inserted_count, updated_count

    except psycopg2.Error as e:
        print(f"⚠️  Database error: {e}")
        raise
    except Exception as e:
        print(f"⚠️  Error saving to database: {e}")
        raise

def sync_single_date(fs, date_str, db_conn, quiet=False):
    """
    Sync nutrition data for a single date.

    Args:
        fs: Fatsecret client instance
        date_str: Date string in YYYY-MM-DD format
        db_conn: Database connection string
        quiet: If True, suppress progress output

    Returns:
        Tuple of (inserted_count, updated_count)
    """
    if not quiet:
        print(f"\nFetching food diary for {date_str}...")

    data = fetch_food_diary(fs, date_str)
    inserted, updated = save_to_neon(data, date_str, db_conn, quiet)

    if not quiet:
        print(f"✓ Success! Data saved to Neon.")

    return inserted, updated

def sync_backfill(fs, days, db_conn, quiet=False):
    """
    Backfill nutrition data for the last N days.

    Args:
        fs: Fatsecret client instance
        days: Number of days to backfill (including today)
        db_conn: Database connection string
        quiet: If True, suppress progress output

    Returns:
        Tuple of (total_inserted, total_updated)
    """
    today = datetime.now()
    dates_to_fetch = [(today - timedelta(days=i)).strftime('%Y-%m-%d')
                      for i in range(days - 1, -1, -1)]

    if not quiet:
        print(f"\n--- Backfilling {days} days ({dates_to_fetch[0]} to {dates_to_fetch[-1]}) ---\n")

    total_inserted = 0
    total_updated = 0

    for date_str in dates_to_fetch:
        if not quiet:
            print(f"Processing {date_str}...", end=" ")

        data = fetch_food_diary(fs, date_str)
        inserted, updated = save_to_neon(data, date_str, db_conn, quiet)

        total_inserted += inserted
        total_updated += updated

    if not quiet:
        print(f"\n✓ Backfill complete!")
        print(f"  Total inserted: {total_inserted}")
        print(f"  Total updated: {total_updated}")

    return total_inserted, total_updated

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Sync nutrition data from FatSecret API to Neon Postgres',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        Interactive mode (prompts for date)
  %(prog)s --date 2024-01-15      Fetch specific date
  %(prog)s --backfill 7           Backfill last 7 days
  %(prog)s --backfill 30 --quiet  Backfill 30 days (quiet, for cron)
  %(prog)s --auth                 Force new OAuth authentication
        """
    )

    parser.add_argument('--date',
                        help='Specific date to fetch (YYYY-MM-DD format)')
    parser.add_argument('--backfill',
                        type=int,
                        metavar='DAYS',
                        help='Backfill last N days (including today)')
    parser.add_argument('--quiet', '-q',
                        action='store_true',
                        help='Quiet mode (minimal output, for cron/CI)')
    parser.add_argument('--auth',
                        action='store_true',
                        help='Force new OAuth authentication flow')

    args = parser.parse_args()

    # Validate credentials
    validate_credentials()

    # Get database connection
    db_conn = os.environ.get('NEON_DB_URL') or os.environ.get('DATABASE_URL')
    if not db_conn:
        if args.quiet:
            print("⚠️  No database connection string found in environment")
            sys.exit(1)
        db_conn = input("Enter your Neon DB Connection String: ").strip()

    if not db_conn or "user:password" in db_conn:
        print("⚠️  Please provide a valid Neon database connection string")
        print("Set NEON_DB_URL or DATABASE_URL environment variable")
        sys.exit(1)

    # Handle auth-only mode
    if args.auth:
        print("\n--- FatSecret Authentication ---")
        fs = get_fatsecret_client(force_auth=True)
        if fs:
            print("\n✓ Authentication complete! Tokens saved.")
            print("You can now run sync operations.")
        else:
            print("\n⚠️  Authentication failed")
            sys.exit(1)
        return

    # Get authenticated client
    if not args.quiet:
        print("--- FatSecret Nutrition Sync ---")

    fs = get_fatsecret_client()
    if fs is None:
        print("\n⚠️  Authentication required. Run with --auth flag first:")
        print(f"  python {sys.argv[0]} --auth")
        sys.exit(1)

    try:
        # Determine operation mode
        if args.backfill:
            # Backfill mode
            sync_backfill(fs, args.backfill, db_conn, args.quiet)

        elif args.date:
            # Specific date mode
            sync_single_date(fs, args.date, db_conn, args.quiet)

        else:
            # Interactive mode
            if args.quiet:
                print("⚠️  Interactive mode requires user input. Use --date or --backfill for automated runs.")
                sys.exit(1)

            # Default to yesterday
            default_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            date_input = input(f"\nEnter date to fetch (YYYY-MM-DD) [default: {default_date}]: ").strip()
            fetch_date = date_input if date_input else default_date

            sync_single_date(fs, fetch_date, db_conn, args.quiet)

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
