#!/usr/bin/env python3
"""
Check what Fitbit data has been loaded into the database
Identifies missing dates and data gaps
"""

import psycopg2
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment
load_dotenv('.env.local')
load_dotenv('.env')

db_conn = os.environ.get('NEON_DB_URL') or os.environ.get('DATABASE_URL')

if not db_conn:
    print("❌ No database connection found!")
    exit(1)

conn = psycopg2.connect(db_conn)
cur = conn.cursor()

print("=== Fitbit Data Status Check ===\n")

# Check last 30 days
end_date = datetime.now().date()
start_date = end_date - timedelta(days=29)

print(f"Checking data from {start_date} to {end_date}\n")

# Check each table
tables_to_check = [
    ('fitbit_activity_daily', 'Activity'),
    ('fitbit_heart_rate', 'Heart Rate'),
    ('fitbit_hrv', 'HRV'),
    ('fitbit_spo2', 'SpO2'),
    ('fitbit_breathing_rate', 'Breathing Rate'),
    ('fitbit_vo2_max', 'VO2 Max'),
    ('fitbit_sleep', 'Sleep'),
    ('fitbit_exercises', 'Exercises')
]

missing_by_table = {}

for table_name, display_name in tables_to_check:
    cur.execute(f"""
        SELECT date::date 
        FROM {table_name} 
        WHERE date >= %s AND date <= %s 
        ORDER BY date
    """, (start_date, end_date))
    
    dates_with_data = set(row[0] for row in cur.fetchall())
    
    # Generate all dates in range
    all_dates = set()
    current = start_date
    while current <= end_date:
        all_dates.add(current)
        current += timedelta(days=1)
    
    missing_dates = sorted(all_dates - dates_with_data)
    missing_by_table[display_name] = missing_dates
    
    print(f"📊 {display_name}:")
    print(f"   ✓ {len(dates_with_data)} days with data")
    if missing_dates:
        print(f"   ✗ {len(missing_dates)} days missing")
    print()

# Show summary of completely missing days
all_missing = set(missing_by_table['Activity'])
for dates in missing_by_table.values():
    all_missing = all_missing.intersection(set(dates))

if all_missing:
    print(f"⚠️  {len(all_missing)} days completely missing from ALL tables:")
    for date in sorted(all_missing)[:10]:  # Show first 10
        print(f"   - {date}")
    if len(all_missing) > 10:
        print(f"   ... and {len(all_missing) - 10} more")
    print()

# Show most recent data
cur.execute("""
    SELECT date, steps, calories_burned 
    FROM fitbit_activity_daily 
    ORDER BY date DESC 
    LIMIT 7
""")

print("📅 Most Recent Activity Data:")
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]:,} steps, {row[2]:,} cal")

# Count exercises
cur.execute("SELECT COUNT(*), COUNT(DISTINCT date) FROM fitbit_exercises")
exercise_count, exercise_days = cur.fetchone()
print(f"\n🏃 Exercises: {exercise_count} workouts across {exercise_days} days")

cur.close()
conn.close()

print("\n✅ Check complete!")
