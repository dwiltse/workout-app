# FatSecret Weight Sync Guide

Unified script for syncing weight data from FatSecret API to Neon Postgres database.

## Quick Start

### 1. Initial Setup

```bash
# Install dependencies (if not already installed)
pip install fatsecret psycopg2-binary python-dotenv requests requests-oauthlib

# Set environment variables in .env.local
FATSECRET_CLIENT_ID=your_consumer_key
FATSECRET_CLIENT_SECRET=your_consumer_secret
NEON_DB_URL=postgresql://user:password@host/database?sslmode=require

# Authenticate once (saves tokens for future use)
python3 fatsecret_weight.py --auth
```

### 2. Usage Examples

```bash
# Interactive mode (prompts for date, defaults to current month)
python3 fatsecret_weight.py

# Fetch specific month
python3 fatsecret_weight.py --date 2024-01-15

# Backfill last 3 months
python3 fatsecret_weight.py --backfill 3

# Backfill last 6 months (quiet mode for automation)
python3 fatsecret_weight.py --backfill 6 --quiet
```

## Features

### ✅ All-in-One Script
- **Single Month**: Fetch weight data for a specific month
- **Backfill**: Bulk import multiple months at once
- **Interactive**: Prompts for date if none specified
- **Automated**: Quiet mode for cron/CI environments

### ✅ Robust Error Handling
- Database connection errors caught and reported
- Context managers prevent resource leaks
- Graceful handling of missing data
- Duplicate prevention via `ON CONFLICT`

### ✅ Complete Data Capture
- Weight in lbs (converted from kg)
- Body fat percentage
- Comments/notes
- Insert/update tracking and reporting

### ✅ Flexible Authentication
- **File cache**: `.fatsecret_tokens.json` (for local use)
- **Environment variables**: `FATSECRET_ACCESS_TOKEN` + `FATSECRET_ACCESS_TOKEN_SECRET` (for CI/cron)
- **Custom cache path**: Set `FATSECRET_TOKEN_CACHE` env var

## Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--date YYYY-MM-DD` | Fetch specific month | `--date 2024-01-15` |
| `--backfill N` | Backfill last N months | `--backfill 3` |
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

Create `.github/workflows/weekly-weight-sync.yml`:

```yaml
name: Weekly Weight Sync

on:
  schedule:
    - cron: '0 10 * * 0'  # 10 AM UTC every Sunday
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

      - name: Sync weight data
        env:
          FATSECRET_CLIENT_ID: ${{ secrets.FATSECRET_CLIENT_ID }}
          FATSECRET_CLIENT_SECRET: ${{ secrets.FATSECRET_CLIENT_SECRET }}
          FATSECRET_ACCESS_TOKEN: ${{ secrets.FATSECRET_ACCESS_TOKEN }}
          FATSECRET_ACCESS_TOKEN_SECRET: ${{ secrets.FATSECRET_ACCESS_TOKEN_SECRET }}
          NEON_DB_URL: ${{ secrets.NEON_DB_URL }}
        run: python3 fatsecret_weight.py --backfill 3 --quiet
```

**Setup GitHub Secrets:**
1. Go to your repo → Settings → Secrets and variables → Actions
2. Add the required secrets listed above
3. To get access tokens, run `fatsecret_weight.py --auth` locally, then copy from `.fatsecret_tokens.json`

### Option 2: Cron Job (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add weekly sync every Sunday at 10 AM
0 10 * * 0 cd /home/dwiltse/projects/workout-app && /usr/bin/python3 fatsecret_weight.py --backfill 3 --quiet >> /var/log/fatsecret-weight-sync.log 2>&1
```

### Option 3: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Weekly, Sunday at 10:00 AM
4. Action: Start a program
   - Program: `C:\Python311\python.exe`
   - Arguments: `fatsecret_weight.py --backfill 3 --quiet`
   - Start in: `C:\path\to\workout-app`

## Database Schema

The script creates and manages the `weight_logs` table:

```sql
CREATE TABLE weight_logs (
    id SERIAL PRIMARY KEY,
    date DATE,
    weight DECIMAL(5,1),           -- Weight in lbs (converted from kg)
    fat_percentage DECIMAL(5,2),   -- Body fat percentage
    comment TEXT,                   -- Optional notes/comments
    entry_id BIGINT UNIQUE          -- FatSecret entry ID (prevents duplicates)
);
```

## How It Works

### Month-Based Fetching
Unlike the nutrition sync (which fetches daily), weight data is fetched by **month**:
- FatSecret API returns all weight entries for a given month
- You provide any date in the month (e.g., `2024-01-15` fetches all January 2024 entries)
- Backfill uses 30-day intervals to cover multiple months

### Data Conversion
- **Weight**: Converted from kg to lbs (multiply by 2.20462)
- **Date**: Converted from `date_int` (days since epoch) to standard date
- **Fat %**: Stored as-is from FatSecret

### Duplicate Prevention
- Uses `entry_id` as unique constraint
- `ON CONFLICT` updates existing entries instead of failing
- Tracks inserts vs updates for reporting

## Troubleshooting

### "No cached tokens found"
Run authentication first:
```bash
python3 fatsecret_weight.py --auth
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

### "No weight data found for month"
This is normal if you haven't logged weight in FatSecret for that month. The script will continue processing other months.

## Comparison with Nutrition Sync

| Feature | Weight Sync | Nutrition Sync |
|---------|-------------|----------------|
| Data Type | Weight, body fat % | Calories, macros, etc. |
| Fetch Interval | Monthly | Daily |
| Table | `weight_logs` | `diet_logs` |
| Backfill Unit | Months | Days |
| API Method | `weights_get_month()` | `food_entries_get()` |

Both scripts share:
- Same authentication system
- Same CLI flag structure
- Same environment variable support
- Compatible for combined scheduling

## Migration from Old Scripts

If you were using `fatsecret_weight_weekly.py`:

| Old Script | New Command |
|------------|-------------|
| `python fatsecret_weight_weekly.py` | `python3 fatsecret_weight.py --backfill 3 --quiet` |

The new script:
- ✅ Uses environment variables (no hardcoded credentials)
- ✅ Supports flexible CLI flags
- ✅ Better error handling with context managers
- ✅ Tracks inserts vs updates
- ✅ Works with both file cache and environment variable tokens

You can safely delete `fatsecret_weight_weekly.py` after verifying the new one works.

## Advanced Usage

### Custom token cache location
```bash
export FATSECRET_TOKEN_CACHE=/path/to/custom/tokens.json
python3 fatsecret_weight.py --backfill 3
```

### Force re-authentication
```bash
python3 fatsecret_weight.py --auth
```

### Backfill large date range
```bash
# Last 12 months
python3 fatsecret_weight.py --backfill 12 --quiet
```

### Use in shell scripts
```bash
#!/bin/bash
# sync-weight.sh

cd /path/to/workout-app
python3 fatsecret_weight.py --backfill 3 --quiet

if [ $? -eq 0 ]; then
    echo "Weight sync completed successfully"
else
    echo "Weight sync failed"
    exit 1
fi
```

### Combined nutrition + weight sync
```bash
#!/bin/bash
# sync-all-fatsecret.sh

# Sync nutrition (last 7 days)
python3 fatsecret_sync.py --backfill 7 --quiet

# Sync weight (last 3 months)
python3 fatsecret_weight.py --backfill 3 --quiet

echo "All FatSecret data synced!"
```

## Support

For issues or questions:
- Check troubleshooting section above
- Review `FATSECRET_API_INTEGRATION.md` for API details
- Check script output for specific error messages
