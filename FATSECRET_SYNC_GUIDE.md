# FatSecret Sync Guide

Unified script for syncing nutrition data from FatSecret API to Neon Postgres database.

## Quick Start

### 1. Initial Setup

```bash
# Install dependencies
pip install fatsecret psycopg2-binary python-dotenv requests requests-oauthlib

# Set environment variables in .env.local
FATSECRET_CLIENT_ID=your_consumer_key
FATSECRET_CLIENT_SECRET=your_consumer_secret
NEON_DB_URL=postgresql://user:password@host/database?sslmode=require

# Authenticate once (saves tokens for future use)
python3 fatsecret_sync.py --auth
```

### 2. Usage Examples

```bash
# Interactive mode (prompts for date, defaults to yesterday)
python3 fatsecret_sync.py

# Fetch specific date
python3 fatsecret_sync.py --date 2024-01-15

# Backfill last 7 days
python3 fatsecret_sync.py --backfill 7

# Backfill last 30 days (quiet mode for automation)
python3 fatsecret_sync.py --backfill 30 --quiet
```

## Features

### ✅ All-in-One Script
- **Single Date**: Fetch nutrition data for a specific date
- **Backfill**: Bulk import multiple days at once
- **Interactive**: Prompts for date if none specified
- **Automated**: Quiet mode for cron/CI environments

### ✅ Robust Error Handling
- Database connection errors caught and reported
- Context managers prevent resource leaks
- Graceful handling of missing data
- Duplicate prevention via `ON CONFLICT`

### ✅ Complete Data Capture
- Calories, protein, carbs, fat, **fiber**
- Meal categorization (Breakfast, Lunch, Dinner, Other)
- Insert/update tracking and reporting

### ✅ Flexible Authentication
- **File cache**: `.fatsecret_tokens.json` (for local use)
- **Environment variables**: `FATSECRET_ACCESS_TOKEN` + `FATSECRET_ACCESS_TOKEN_SECRET` (for CI/cron)
- **Custom cache path**: Set `FATSECRET_TOKEN_CACHE` env var

## Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--date YYYY-MM-DD` | Fetch specific date | `--date 2024-01-15` |
| `--backfill N` | Backfill last N days | `--backfill 7` |
| `--quiet`, `-q` | Minimal output (for cron) | `--quiet` |
| `--auth` | Force new OAuth authentication | `--auth` |
| `--help`, `-h` | Show help message | `--help` |

## Environment Variables

### Required
```bash
FATSECRET_CLIENT_ID           # FatSecret API consumer key
FATSECRET_CLIENT_SECRET       # FatSecret API consumer secret
NEON_DB_URL                   # Postgres connection string
```

### Optional
```bash
DATABASE_URL                  # Alternative to NEON_DB_URL
FATSECRET_ACCESS_TOKEN        # Pre-configured OAuth token (for CI)
FATSECRET_ACCESS_TOKEN_SECRET # Pre-configured OAuth secret (for CI)
FATSECRET_TOKEN_CACHE         # Token cache file path (default: .fatsecret_tokens.json)
```

## Scheduling Options

### Option 1: GitHub Actions (Recommended)

Create `.github/workflows/daily-nutrition-sync.yml`:

```yaml
name: Daily Nutrition Sync

on:
  schedule:
    - cron: '0 6 * * *'  # 6 AM UTC daily
  workflow_dispatch:      # Manual trigger button

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install fatsecret psycopg2-binary python-dotenv requests requests-oauthlib

      - name: Sync nutrition data
        env:
          FATSECRET_CLIENT_ID: ${{ secrets.FATSECRET_CLIENT_ID }}
          FATSECRET_CLIENT_SECRET: ${{ secrets.FATSECRET_CLIENT_SECRET }}
          FATSECRET_ACCESS_TOKEN: ${{ secrets.FATSECRET_ACCESS_TOKEN }}
          FATSECRET_ACCESS_TOKEN_SECRET: ${{ secrets.FATSECRET_ACCESS_TOKEN_SECRET }}
          NEON_DB_URL: ${{ secrets.NEON_DB_URL }}
        run: python3 fatsecret_sync.py --backfill 7 --quiet
```

**Setup GitHub Secrets:**
1. Go to your repo → Settings → Secrets and variables → Actions
2. Add the required secrets listed above
3. To get access tokens, run `fatsecret_sync.py --auth` locally, then copy from `.fatsecret_tokens.json`

### Option 2: Cron Job (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add daily sync at 6 AM
0 6 * * * cd /home/dwiltse/projects/workout-app && /usr/bin/python3 fatsecret_sync.py --backfill 7 --quiet >> /var/log/fatsecret-sync.log 2>&1
```

### Option 3: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 6:00 AM
4. Action: Start a program
   - Program: `C:\Python311\python.exe`
   - Arguments: `fatsecret_sync.py --backfill 7 --quiet`
   - Start in: `C:\path\to\workout-app`

## Database Schema

The script creates and manages the `diet_logs` table:

```sql
CREATE TABLE diet_logs (
    id SERIAL PRIMARY KEY,
    date DATE,
    meal VARCHAR(50),               -- Breakfast, Lunch, Dinner, Other
    food_name VARCHAR(255),         -- Name of food item
    calories DECIMAL,               -- Total calories
    protein DECIMAL,                -- Protein (grams)
    carbs DECIMAL,                  -- Carbohydrates (grams)
    fat DECIMAL,                    -- Total fat (grams)
    fiber DECIMAL,                  -- Fiber (grams)
    sugar DECIMAL,                  -- Sugar (grams)
    sodium DECIMAL,                 -- Sodium (mg)
    saturated_fat DECIMAL,          -- Saturated fat (grams)
    polyunsaturated_fat DECIMAL,    -- Polyunsaturated fat (grams)
    monounsaturated_fat DECIMAL,    -- Monounsaturated fat (grams)
    cholesterol DECIMAL,            -- Cholesterol (mg)
    potassium DECIMAL,              -- Potassium (mg)
    entry_id BIGINT UNIQUE          -- FatSecret entry ID (prevents duplicates)
);
```

**Note:** The script automatically adds new columns to existing tables on first run.

## Troubleshooting

### "No cached tokens found"
Run authentication first:
```bash
python3 fatsecret_sync.py --auth
```

### "Missing FatSecret credentials"
Ensure environment variables are set:
```bash
export FATSECRET_CLIENT_ID=your_key
export FATSECRET_CLIENT_SECRET=your_secret
```

Or add them to `.env.local`.

### "Database error: connection refused"
Check your `NEON_DB_URL` connection string format:
```
postgresql://user:password@host/database?sslmode=require
```

### GitHub Actions failing
1. Verify all secrets are added to your repo
2. Check that token secrets are valid (run `--auth` locally to get fresh tokens)
3. Review Actions logs for specific error messages

## Migration from Old Scripts

If you were using `fatsecret_migration.py` or `fatsecret_backfill.py`:

| Old Script | New Command |
|------------|-------------|
| `python fatsecret_migration.py` | `python3 fatsecret_sync.py` |
| `python fatsecret_backfill.py` | `python3 fatsecret_sync.py --backfill 7` |

The new script:
- ✅ Includes all fixes (fiber field, better error handling, context managers)
- ✅ Supports both interactive and automated modes
- ✅ Works with both file cache and environment variable tokens
- ✅ Provides better progress reporting

You can safely delete the old scripts after verifying the new one works.

## Advanced Usage

### Custom token cache location
```bash
export FATSECRET_TOKEN_CACHE=/path/to/custom/tokens.json
python3 fatsecret_sync.py --backfill 7
```

### Force re-authentication
```bash
python3 fatsecret_sync.py --auth
```

### Backfill large date range
```bash
# Last 90 days
python3 fatsecret_sync.py --backfill 90 --quiet
```

### Use in shell scripts
```bash
#!/bin/bash
# sync-nutrition.sh

cd /path/to/workout-app
python3 fatsecret_sync.py --backfill 7 --quiet

if [ $? -eq 0 ]; then
    echo "Nutrition sync completed successfully"
else
    echo "Nutrition sync failed"
    exit 1
fi
```

## Support

For issues or questions:
- Check troubleshooting section above
- Review `FATSECRET_API_INTEGRATION.md` for API details
- Check script output for specific error messages
