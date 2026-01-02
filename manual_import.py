import csv
import psycopg2
import time

# --- CONFIGURATION ---
# Neon Database Connection String (Same as fatsecret_migration.py)
DB_CONNECTION_STRING = "postgres://user:password@ep-xyz.aws.neon.tech/neondb?sslmode=require"
CSV_FILE_PATH = 'manual_data/myfitnesspal_import.csv'
# ---------------------

def import_csv_to_neon():
    try:
        conn = psycopg2.connect(DB_CONNECTION_STRING)
        cur = conn.cursor()
        
        # Ensure table exists (same schema as FatSecret script)
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
        
        with open(CSV_FILE_PATH, 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                # Generate a unique fake ID for manual entries based on time + count
                # Using negative numbers to distinguish from FatSecret API IDs
                fake_id = -1 * int(time.time() * 1000) - count
                
                cur.execute("""
                    INSERT INTO diet_logs (date, meal, food_name, calories, protein, carbs, fat, entry_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (entry_id) DO NOTHING;
                """, (
                    row['date'],
                    row['meal'],
                    row['food_name'],
                    row['calories'],
                    row['protein'],
                    row['carbs'],
                    row['fat'],
                    fake_id
                ))
                count += 1
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"Success! Imported {count} manual entries into Neon.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Prompt for DB string if default
    if "user:password" in DB_CONNECTION_STRING:
        DB_CONNECTION_STRING = input("Enter your Neon DB Connection String: ").strip()
        
    import_csv_to_neon()
