# Scripts Directory

Utility scripts for the workout app project.

## Available Scripts

### export_to_sql.sh

Exports Neon Postgres database to SQL file for:
- Migration to Databricks Lakebase
- Database backups
- Data analysis

**Usage:**
```bash
# 1. Update connection details in the script
nano scripts/export_to_sql.sh

# 2. Make executable
chmod +x scripts/export_to_sql.sh

# 3. Run export
./scripts/export_to_sql.sh
```

**Output:**
- File saved to: `exports/neon_export.sql`
- Automatic backups with timestamps
- Typical size: 5-20 MB

**What's exported:**
- Fitbit data (8 tables): activity, heart rate, HRV, SpO2, breathing rate, VO2 max, sleep, exercises
- FatSecret data (2 tables): diet logs, weight logs
- Legacy tables (6 tables): exercises, routines, workout logs, workout sets

**What's excluded (too large):**
- GPS tracking points
- Route data
- Exercise TCX files

### create-icons.js

Generates app icons for Next.js.

### import-exercises.js

Imports exercise reference data into the database.

## Related Documentation

For Databricks migration:
- See `../lakebase_workout_app/databricks/06_lakebase_setup_guide.md`
- After exporting, copy `exports/neon_export.sql` to the Databricks project
