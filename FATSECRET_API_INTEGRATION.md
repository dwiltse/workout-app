# FatSecret API Integration Guide

## Overview
Successfully integrated FatSecret API to automatically extract daily food diary entries into Neon PostgreSQL database. This eliminates the need for manual CSV exports and enables real-time data syncing.

## The Problem
Initially wanted to use MyFitnessPal's API, but pivoted to FatSecret for better API availability. The goal: automatically pull food entries (calories, protein, carbs, fat) and store them in the database for the workout tracker app.

## Solution Architecture

### Authentication: OAuth 1.0 (3-Legged)
FatSecret requires OAuth 1.0 "3-Legged OAuth" for personal diary access (not OAuth 2.0).

**Credentials:**
- Consumer Key & Secret: Stored in `.fatsecret_tokens.json` (human-readable, gitignored)
- Access Token & Secret: Also in `.fatsecret_tokens.json`

**Token Flow:**
1. User authorizes app via browser
2. Receives verification code
3. Tokens saved to `.fatsecret_tokens.json` for future use
4. Subsequent runs use cached tokens (no re-auth needed)

### Key Technical Challenges & Solutions

#### ❌ Challenge 1: Wrong OAuth Flow
**Problem:** Initially tried OAuth 2.0 "Client Credentials" flow
- FatSecret doesn't support this for personal data access
- Got 403 Forbidden errors

**Solution:** Switched to OAuth 1.0 "3-Legged OAuth" using `fatsecret` Python library

#### ❌ Challenge 2: Manual OAuth Signing Failed
**Problem:** Attempted manual OAuth signing with `oauthlib` library
- Signature validation failures
- Complex request building

**Solution:** Used `fatsecret` library which handles OAuth signing automatically

#### ❌ Challenge 3: Token Passing Issue
**Problem:** Tried to set tokens as attributes after client creation
```python
fs = Fatsecret(CONSUMER_KEY, CONSUMER_SECRET)
fs.access_token = token  # ❌ Didn't work
```
- Got "Error 2: This api call requires an authenticated session"

**Solution:** Pass tokens to constructor as `session_token` tuple
```python
fs = Fatsecret(
    CONSUMER_KEY, 
    CONSUMER_SECRET,
    session_token=(access_token, access_token_secret)  # ✅ Works
)
```

#### ❌ Challenge 4: Date Format Validation
**Problem:** API rejected date parameters in multiple formats
- `"2025-12-31"` → "Invalid integer value: please check your date"
- `"20251231"` → "An unknown error occurred"

**Solution:** Pass `datetime` object instead of string
```python
date_obj = datetime.strptime(date_str, '%Y-%m-%d')
diary = fs.food_entries_get(date=date_obj)  # ✅ Works
```
The library automatically converts datetime to "days since epoch" (Unix time format FatSecret expects)

#### ❌ Challenge 5: API Response Format Changed
**Problem:** Expected nested dict structure but got list
```python
data.get('food_entries', {}).get('food_entry', [])  # ❌ Failed
```

**Solution:** Handle both formats
```python
if isinstance(data, list):
    entries = data
else:
    entries = data.get('food_entries', {}).get('food_entry', [])
```

#### ❌ Challenge 6: Pickle Tokens (Security Risk)
**Problem:** Used Python pickle for token storage
- Not portable (Python-only)
- Security risk (code execution vulnerability)
- Not human-readable

**Solution:** Switched to JSON format
- Human-readable
- Portable
- Same gitignore protection
- Converted existing tokens automatically

## Database Schema

```sql
CREATE TABLE diet_logs (
    id SERIAL PRIMARY KEY,
    date DATE,
    meal VARCHAR(50),
    food_name VARCHAR(255),
    calories DECIMAL,
    protein DECIMAL,
    carbs DECIMAL,
    fat DECIMAL,
    entry_id BIGINT UNIQUE  -- Prevents duplicate imports
);
```

**Key Feature:** `ON CONFLICT (entry_id) DO NOTHING` prevents duplicate entries if scripts run multiple times.

## Scripts

### 1. `fatsecret_migration.py` - Daily Import
Imports food entries for a specific date (default: yesterday).

```bash
python fatsecret_migration.py
```

**Features:**
- Auto-loads cached tokens (no auth needed after first run)
- Prompts for date (YYYY-MM-DD format)
- Inserts data to Neon database
- Skips duplicates silently

**First Run:** Requires browser authorization via verification code
**Subsequent Runs:** Silent, uses cached tokens from `.fatsecret_tokens.json`

### 2. `fatsecret_backfill.py` - 7-Day Backfill
Imports food entries for the last 7 days (including today).

```bash
python fatsecret_backfill.py
```

**Features:**
- Fetches last 8 days of data
- Shows insert/duplicate counts per day
- Safe to run multiple times (duplicate protection)
- Useful for filling historical data gaps

**Example Output:**
```
Processing 2025-12-25... (0 new, 0 duplicates)
Processing 2025-12-29... (10 new, 0 duplicates)
Processing 2026-01-01... (0 new, 12 duplicates)  # Already imported
```

## Setup Instructions

### Initial Setup (One-Time)
1. Both scripts installed in project root
2. FatSecret tokens already cached in `.fatsecret_tokens.json`
3. Database table already created in Neon

### Running Daily
```bash
python fatsecret_migration.py
# Enter connection string
# Enter date (or leave blank for yesterday)
```

### Running Weekly
```bash
python fatsecret_backfill.py
# Enter connection string
# Automatically processes last 7 days, skips duplicates
```

## Tested Data
- ✅ Retrieved 12 food entries for Jan 1, 2026
- ✅ Spanning 4 meal types: Breakfast, Lunch, Dinner, Other
- ✅ Total: 1,640 calories
- ✅ All nutritional fields captured: protein, carbs, fat

## Libraries Used
```python
# API
fatsecret        # FatSecret API client with OAuth 1.0
requests          # HTTP library
requests-oauthlib # OAuth signing (used by fatsecret)

# Database
psycopg2-binary   # PostgreSQL connector

# Utilities
json              # Token storage
datetime          # Date handling
os                # File operations
```

## What's Next
- [ ] Integrate Fitbit/device activity data (ACTIVITY.csv)
- [ ] Add Caliber app workout data
- [ ] Integrate weight tracking
- [ ] Build dashboard combining all data sources
- [ ] Consider automated scheduling (cron/Task Scheduler)

## Key Takeaways
1. **OAuth 1.0 vs 2.0:** Know your API's requirements—FatSecret uses older but still-secure OAuth 1.0
2. **Use Libraries:** Don't manually sign OAuth requests—use official/trusted libraries
3. **Token Management:** Store securely (JSON, env vars, keyring)—avoid pickle
4. **Idempotent Operations:** Design imports with duplicate protection (UNIQUE constraints)
5. **Test Edge Cases:** Multiple runs, missing data, format variations

---

**Status:** ✅ Complete and working (as of Jan 1, 2026)
