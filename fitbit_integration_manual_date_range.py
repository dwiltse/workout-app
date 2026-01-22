#!/usr/bin/env python3
"""
Fitbit API Integration - Manual Date Range Version
Allows you to specify exact start and end dates for syncing
Use this for backfilling historical data
"""

# Import everything from the main integration script
from fitbit_integration import *

def main():
    print("=== Fitbit Data Sync (Manual Date Range) ===\n")

    # Database connection
    db_conn = os.environ.get('NEON_DB_URL') or os.environ.get('DATABASE_URL')

    if not db_conn:
        print("❌ No database connection found!")
        print("Add DATABASE_URL or NEON_DB_URL to your .env.local file")
        return

    # Create tables if needed
    create_tables_if_needed(db_conn)

    # Initialize Fitbit API
    fitbit = FitbitAPI()

    # Check if we need to authorize
    if not fitbit.access_token:
        print("No existing authorization found. Starting OAuth flow...")
        fitbit.authorize()

    # Get date range from user
    print("\nEnter the date range to sync (YYYY-MM-DD format)")
    start_date_str = input("Start date (e.g., 2025-12-20): ").strip()
    end_date_str = input("End date (e.g., 2026-01-12): ").strip()

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        print("❌ Invalid date format. Use YYYY-MM-DD")
        return

    if start_date > end_date:
        print("❌ Start date must be before end date")
        return

    days_count = (end_date - start_date).days + 1
    print(f"\nSyncing Fitbit data from {start_date} to {end_date} ({days_count} days)...")
    
    # API rate limit warning
    if days_count > 7:
        print(f"⚠️  Note: Syncing {days_count} days. Fitbit API has rate limits (150 req/hour).")
        print(f"   This will take approximately {days_count * 2} seconds with 2-second delays.")
        proceed = input("   Continue? (y/n): ").strip().lower()
        if proceed != 'y':
            print("Cancelled.")
            return

    # Fetch and save data for each day
    total_days = 0
    success_days = 0

    current_date = start_date
    while current_date <= end_date:
        try:
            print(f"\nProcessing {current_date}...")

            # Gather all data for this date
            fitbit_data = {}

            # Activity data (steps, calories, etc.)
            try:
                activity_data = fitbit.get_daily_activity(current_date)
                fitbit_data['activity'] = activity_data
                print(f"  ✓ Activity: {activity_data.get('summary', {}).get('steps', 0)} steps")
            except Exception as e:
                print(f"  ✗ Activity data error: {e}")

            # Heart rate data
            try:
                hr_data = fitbit.get_heart_rate(current_date)
                fitbit_data['heart_rate'] = hr_data
                if hr_data.get('activities-heart'):
                    rhr = hr_data['activities-heart'][0].get('value', {}).get('restingHeartRate')
                    print(f"  ✓ Heart rate: RHR {rhr if rhr else 'N/A'}")
            except Exception as e:
                print(f"  ✗ Heart rate data error: {e}")

            # Sleep data
            try:
                sleep_data = fitbit.get_sleep_data(current_date)
                fitbit_data['sleep'] = sleep_data
                sleep_logs = sleep_data.get('sleep', [])
                print(f"  ✓ Sleep: {len(sleep_logs)} log(s)")
            except Exception as e:
                print(f"  ✗ Sleep data error: {e}")

            # HRV data
            try:
                hrv_data = fitbit.get_hrv_data(current_date)
                fitbit_data['hrv'] = hrv_data
                if hrv_data.get('hrv'):
                    print(f"  ✓ HRV: Available")
            except Exception as e:
                print(f"  ✗ HRV data error: {e}")

            # SpO2 data
            try:
                spo2_data = fitbit.get_spo2_data(current_date)
                fitbit_data['spo2'] = spo2_data
                if spo2_data:
                    avg = spo2_data.get('value', {}).get('avg')
                    if avg:
                        print(f"  ✓ SpO2: {avg}%")
            except Exception as e:
                print(f"  ✗ SpO2 data error: {e}")

            # Breathing Rate data
            try:
                br_data = fitbit.get_breathing_rate(current_date)
                fitbit_data['breathing_rate'] = br_data
                if br_data.get('br'):
                    print(f"  ✓ Breathing Rate: Available")
            except Exception as e:
                print(f"  ✗ Breathing rate error: {e}")

            # VO2 Max data
            try:
                vo2_data = fitbit.get_vo2_max(current_date)
                fitbit_data['vo2_max'] = vo2_data
                if vo2_data.get('cardioScore'):
                    print(f"  ✓ VO2 Max: Available")
            except Exception as e:
                print(f"  ✗ VO2 Max data error: {e}")

            # Exercise logs with GPS data
            try:
                exercises = fitbit.get_exercise_log(current_date)

                # For each exercise, check if it has GPS data and fetch TCX
                for exercise in exercises:
                    log_id = exercise.get('logId')
                    has_gps = exercise.get('hasGPS', False)

                    if has_gps:
                        try:
                            print(f"    📍 Fetching GPS data for {exercise.get('activityName', 'Unknown')} ({log_id})")
                            tcx_data = fitbit.get_activity_tcx(log_id)

                            if tcx_data:
                                # Parse TCX data
                                gps_points, route_data = fitbit.parse_tcx_data(tcx_data, log_id)
                                exercise['tcx_data'] = tcx_data
                                exercise['gps_points'] = gps_points
                                exercise['route_data'] = route_data

                                if route_data and route_data['gps_points_count'] > 0:
                                    print(f"      ✓ {route_data['gps_points_count']} GPS points, {route_data['total_distance_miles']:.2f} mi")
                                else:
                                    print(f"      ⚠ GPS data found but no valid points extracted")
                            else:
                                print(f"      ⚠ No TCX data available for exercise {log_id}")

                        except Exception as tcx_error:
                            print(f"      ✗ Error fetching GPS data: {tcx_error}")

                fitbit_data['exercises'] = exercises
                print(f"  ✓ Exercises: {len(exercises)} log(s)")
            except Exception as e:
                print(f"  ✗ Exercise data error: {e}")

            # Save to database
            if fitbit_data:
                save_to_database(fitbit_data, current_date, db_conn)
                success_days += 1

            total_days += 1
            current_date += timedelta(days=1)

            # Rate limiting - small delay between days to avoid hitting API limits
            if current_date <= end_date:  # Don't delay on the last day
                time.sleep(2)  # 2-second delay between days

        except Exception as e:
            print(f"✗ Error processing {current_date}: {e}")
            current_date += timedelta(days=1)
            total_days += 1

    print(f"\n=== Sync Complete ===")
    print(f"Successfully processed: {success_days}/{total_days} days")
    print(f"Data saved to database: {db_conn.split('@')[1].split('/')[0] if '@' in db_conn else 'database'}")

if __name__ == "__main__":
    main()
