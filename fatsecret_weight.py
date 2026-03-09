#!/usr/bin/env python3
"""
FatSecret Weight Data Sync Tool

Syncs weight data from FatSecret API to Neon Postgres database.
Supports both single-month fetching and multi-month backfill operations.

Usage:
    # Interactive mode (prompts for date)
    python fatsecret_weight.py

    # Fetch specific month
    python fatsecret_weight.py --date 2024-01-15

    # Backfill last 3 months
    python fatsecret_weight.py --backfill 3

    # Backfill last 6 months (quiet mode for cron)
    python fatsecret_weight.py --backfill 6 --quiet

    # Initial OAuth authentication
    python fatsecret_weight.py --auth

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

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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

def fetch_weight_data(fs, date_str, quiet=False):
    """
    Fetches weight entries for a specific month.

    Args:
        fs: Fatsecret client instance
        date_str: Date string in YYYY-MM-DD format (any day in the desired month)
        quiet: If True, suppress progress output

    Returns:
        Weight entries data (list)
    """
    if not quiet:
        print(f"Fetching weight data for month containing {date_str}...")
    try:
        # Convert string date to datetime object
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')

        # The library fetches all weights for the month
        weights = fs.weights_get_month(date=date_obj)
        return weights
    except KeyError:
        # No weight entries for that month
        if not quiet:
            print(f"  No weight data found for month {date_str}")
        return []
    except Exception as e:
        if not quiet:
            print(f"  ⚠️  Error fetching {date_str}: {e}")
        return []

def save_to_neon(data, db_conn, quiet=False):
    """
    Saves the fetched weight data into Neon Postgres.

    Args:
        data: Weight data from FatSecret API
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

                if not quiet:
                    print(f"  Found {len(entries)} entries", end="")

                inserted_count = 0
                updated_count = 0

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

                        # Store current count to detect if this is insert or update
                        cur.execute("SELECT COUNT(*) FROM weight_logs WHERE entry_id = %s",
                                   (entry_id,))
                        exists_before = cur.fetchone()[0] > 0

                        cur.execute("""
                            INSERT INTO weight_logs (date, weight, fat_percentage, comment, entry_id)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (entry_id) DO UPDATE SET
                                date = EXCLUDED.date,
                                weight = EXCLUDED.weight,
                                fat_percentage = EXCLUDED.fat_percentage,
                                comment = EXCLUDED.comment;
                        """, (date_val, weight_lbs, fat_pct, comment, entry_id))

                        if exists_before:
                            updated_count += 1
                        else:
                            inserted_count += 1

                    except Exception as e:
                        if not quiet:
                            print(f"\n  ⚠️  Error inserting weight entry: {e}")

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

def sync_single_month(fs, date_str, db_conn, quiet=False):
    """
    Sync weight data for a single month.

    Args:
        fs: Fatsecret client instance
        date_str: Date string in YYYY-MM-DD format (any day in the desired month)
        db_conn: Database connection string
        quiet: If True, suppress progress output

    Returns:
        Tuple of (inserted_count, updated_count)
    """
    if not quiet:
        print(f"\nProcessing month containing {date_str}...")

    data = fetch_weight_data(fs, date_str, quiet)
    inserted, updated = save_to_neon(data, db_conn, quiet)

    if not quiet:
        print(f"✓ Success! Data saved to Neon.")

    return inserted, updated

def sync_backfill(fs, months, db_conn, quiet=False):
    """
    Backfill weight data for the last N months.

    Args:
        fs: Fatsecret client instance
        months: Number of months to backfill (including current month)
        db_conn: Database connection string
        quiet: If True, suppress progress output

    Returns:
        Tuple of (total_inserted, total_updated)
    """
    today = datetime.now()
    months_to_fetch = [(today - timedelta(days=30*i)).strftime('%Y-%m-%d')
                       for i in range(months - 1, -1, -1)]

    if not quiet:
        print(f"\n--- Backfilling {months} months ---\n")

    total_inserted = 0
    total_updated = 0

    for date_str in months_to_fetch:
        if not quiet:
            print(f"Processing month containing {date_str}...", end=" ")

        data = fetch_weight_data(fs, date_str, quiet)
        inserted, updated = save_to_neon(data, db_conn, quiet)

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
        description='Sync weight data from FatSecret API to Neon Postgres',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        Interactive mode (prompts for date)
  %(prog)s --date 2024-01-15      Fetch specific month
  %(prog)s --backfill 3           Backfill last 3 months
  %(prog)s --backfill 6 --quiet   Backfill 6 months (quiet, for cron)
  %(prog)s --auth                 Force new OAuth authentication
        """
    )

    parser.add_argument('--date',
                        help='Specific date to fetch month for (YYYY-MM-DD format)')
    parser.add_argument('--backfill',
                        type=int,
                        metavar='MONTHS',
                        help='Backfill last N months (including current month)')
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

    if not db_conn:
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
        print("--- FatSecret Weight Sync ---")

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
            # Specific month mode
            sync_single_month(fs, args.date, db_conn, args.quiet)

        else:
            # Interactive mode
            if args.quiet:
                print("⚠️  Interactive mode requires user input. Use --date or --backfill for automated runs.")
                sys.exit(1)

            # Default to current month
            default_date = datetime.now().strftime('%Y-%m-%d')
            date_input = input(f"\nEnter date for month to fetch (YYYY-MM-DD) [default: {default_date}]: ").strip()
            fetch_date = date_input if date_input else default_date

            sync_single_month(fs, fetch_date, db_conn, args.quiet)

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
