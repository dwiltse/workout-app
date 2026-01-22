# Fitbit Integration - GitHub Actions Setup

Guide to automate daily Fitbit data sync to Neon database using GitHub Actions.

---

## Prerequisites

- Fitbit Developer App configured (CLIENT_ID and CLIENT_SECRET)
- Neon Postgres database with Fitbit tables created
- OAuth tokens obtained (run script locally once first)

---

## Step 1: Obtain OAuth Tokens Locally

**Run the script once locally to complete OAuth:**

```bash
# Set environment variables
export FITBIT_CLIENT_ID=your_client_id
export FITBIT_CLIENT_SECRET=your_client_secret
export DATABASE_URL=your_neon_connection_string

# Run script - will open browser for OAuth
python3 fitbit_integration.py
```

This creates `.fitbit_tokens.json` with your access and refresh tokens.

---

## Step 2: Store Tokens in Neon Database

**Create a tokens table in Neon:**

```sql
CREATE TABLE IF NOT EXISTS fitbit_tokens (
  id INTEGER PRIMARY KEY DEFAULT 1,
  access_token TEXT NOT NULL,
  refresh_token TEXT NOT NULL,
  updated_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT single_row CHECK (id = 1)
);
```

**Copy tokens from file to database:**

```bash
# Manual insert (get tokens from .fitbit_tokens.json)
psql $DATABASE_URL -c "
  INSERT INTO fitbit_tokens (access_token, refresh_token)
  VALUES ('your_access_token', 'your_refresh_token')
  ON CONFLICT (id) DO UPDATE
    SET access_token = EXCLUDED.access_token,
        refresh_token = EXCLUDED.refresh_token,
        updated_at = NOW();
"
```

---

## Step 3: Modify Script for DB Token Storage

**Update `load_tokens()` and `save_tokens()` methods:**

```python
def load_tokens(self):
    """Load tokens from database instead of file"""
    db_conn = os.environ.get('NEON_DB_URL') or os.environ.get('DATABASE_URL')
    if not db_conn:
        return

    try:
        conn = psycopg2.connect(db_conn)
        cur = conn.cursor()
        cur.execute("SELECT access_token, refresh_token FROM fitbit_tokens WHERE id = 1")
        result = cur.fetchone()
        if result:
            self.access_token, self.refresh_token = result
            print("✓ Loaded Fitbit tokens from database")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️  Could not load tokens from database: {e}")

def save_tokens(self, access_token, refresh_token):
    """Save tokens to database instead of file"""
    db_conn = os.environ.get('NEON_DB_URL') or os.environ.get('DATABASE_URL')
    if not db_conn:
        return

    try:
        conn = psycopg2.connect(db_conn)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO fitbit_tokens (id, access_token, refresh_token, updated_at)
            VALUES (1, %s, %s, NOW())
            ON CONFLICT (id) DO UPDATE
                SET access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token,
                    updated_at = NOW()
        """, (access_token, refresh_token))
        conn.commit()
        cur.close()
        conn.close()
        print("✓ Saved Fitbit tokens to database")
    except Exception as e:
        print(f"⚠️  Could not save tokens to database: {e}")
```

---

## Step 4: Add GitHub Secrets

Go to your GitHub repo → Settings → Secrets and variables → Actions

**Add these secrets:**

- `FITBIT_CLIENT_ID` - Your Fitbit app client ID
- `FITBIT_CLIENT_SECRET` - Your Fitbit app client secret
- `NEON_DB_URL` - Your Neon Postgres connection string

---

## Step 5: Create GitHub Actions Workflow

**Create `.github/workflows/fitbit-sync.yml`:**

```yaml
name: Fitbit Data Sync

on:
  schedule:
    # Run daily at 8 AM UTC (adjust timezone as needed)
    - cron: '0 8 * * *'

  # Allow manual trigger from Actions tab
  workflow_dispatch:

jobs:
  sync-fitbit-data:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install psycopg2-binary requests python-dotenv

      - name: Sync Fitbit data to Neon
        env:
          FITBIT_CLIENT_ID: ${{ secrets.FITBIT_CLIENT_ID }}
          FITBIT_CLIENT_SECRET: ${{ secrets.FITBIT_CLIENT_SECRET }}
          DATABASE_URL: ${{ secrets.NEON_DB_URL }}
        run: |
          python3 fitbit_integration.py

      - name: Report status
        if: always()
        run: |
          if [ $? -eq 0 ]; then
            echo "✓ Fitbit sync completed successfully"
          else
            echo "✗ Fitbit sync failed"
            exit 1
          fi
```

---

## Step 6: Test the Workflow

1. **Manual test:** Go to Actions tab → "Fitbit Data Sync" → "Run workflow"
2. **Check logs:** Verify sync completed without errors
3. **Verify data:** Query Neon database to confirm data was inserted

```sql
-- Check latest activity data
SELECT * FROM fitbit_activity_daily ORDER BY date DESC LIMIT 3;

-- Check if GPS routes were saved
SELECT * FROM fitbit_routes ORDER BY route_date DESC LIMIT 5;
```

---

## Troubleshooting

### Token Expired Error

If refresh fails, re-run OAuth locally and update database tokens manually.

### Rate Limit (429 Error)

Reduce `--days` parameter or increase sleep delay between requests.

### Missing Data

- Fitbit sometimes delays processing sleep/HRV data by 1-2 days
- The 3-day lookback window catches delayed data on subsequent runs

### Database Connection Issues

Verify `NEON_DB_URL` secret is formatted correctly:
```
postgresql://user:password@host/database?sslmode=require
```

---

## Optional: Email Notifications on Failure

Add to workflow:

```yaml
- name: Notify on failure
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: Fitbit Sync Failed
    body: Check GitHub Actions logs for details
    to: your-email@example.com
    from: GitHub Actions
```

---

## What the Script Does Daily

1. Connects to Neon database
2. Loads OAuth tokens from `fitbit_tokens` table
3. Fetches last 3 days of Fitbit data:
   - Daily activity (steps, calories, distance)
   - Heart rate zones and resting HR
   - Sleep logs
   - HRV, SpO2, breathing rate, VO2 Max
   - Exercise logs with GPS routes (TCX data)
4. Saves to Neon using UPSERT (no duplicates)
5. Refreshes OAuth tokens if expired
6. Saves updated tokens back to database

**API Efficiency:** ~24-30 API calls per run (well under 150/hour limit)

---

## Maintenance

- **Monthly:** Verify workflow is running successfully
- **Quarterly:** Check OAuth tokens are refreshing properly
- **As needed:** Backfill historical data using `--start-date` / `--end-date` flags

```bash
# Backfill example (run locally or manually trigger with modified workflow)
python3 fitbit_integration.py --start-date 2024-12-01 --end-date 2024-12-31
```
