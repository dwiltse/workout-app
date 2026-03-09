#!/usr/bin/env python3
"""
Fitbit API Integration for Personal Health Data
Fetches steps, workouts, heart rate, and sleep data from Fitbit API
"""

import requests
import psycopg2
from psycopg2.extras import execute_values
import json
import os
from datetime import datetime, timedelta
import webbrowser
from urllib.parse import urlparse, parse_qs, urlencode
import base64
import hashlib
import secrets
import xml.etree.ElementTree as ET
import time
import stat
import argparse

# Load environment variables from .env files
try:
    from dotenv import load_dotenv
    # Try .env.local first (Next.js convention), then .env
    load_dotenv('.env.local')
    load_dotenv('.env')  # Won't override existing vars
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Falling back to system environment variables...")

# Fitbit App Configuration
CLIENT_ID = os.environ.get('FITBIT_CLIENT_ID')
CLIENT_SECRET = os.environ.get('FITBIT_CLIENT_SECRET')
REDIRECT_URI = 'http://127.0.0.1:8080/'
AUTH_URL = 'https://www.fitbit.com/oauth2/authorize'
TOKEN_URL = 'https://api.fitbit.com/oauth2/token'
API_BASE_URL = 'https://api.fitbit.com/1'

# Validate required environment variables
if not CLIENT_ID or not CLIENT_SECRET:
    print("\n⚠️  Missing Fitbit credentials!")
    print("Set environment variables: FITBIT_CLIENT_ID and FITBIT_CLIENT_SECRET")
    print("\nExample:")
    print("export FITBIT_CLIENT_ID=your_client_id")
    print("export FITBIT_CLIENT_SECRET=your_client_secret")
    exit(1)

TOKEN_CACHE_FILE = '.fitbit_tokens.json'

class FitbitAPI:
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.redirect_uri = REDIRECT_URI
        self.access_token = None
        self.refresh_token = None
        self.load_tokens()

    def load_tokens(self):
        """Load saved access tokens from file"""
        if os.path.exists(TOKEN_CACHE_FILE):
            with open(TOKEN_CACHE_FILE, 'r') as f:
                tokens = json.load(f)
                self.access_token = tokens.get('access_token')
                self.refresh_token = tokens.get('refresh_token')
                print("✓ Loaded cached Fitbit tokens")

    def save_tokens(self, access_token, refresh_token):
        """Save tokens to file for future use"""
        tokens = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'created_at': datetime.now().isoformat()
        }
        with open(TOKEN_CACHE_FILE, 'w') as f:
            json.dump(tokens, f, indent=2)
        # Set secure file permissions (owner read/write only)
        os.chmod(TOKEN_CACHE_FILE, stat.S_IRUSR | stat.S_IWUSR)
        print("✓ Saved Fitbit tokens to cache")

    def _get_basic_auth_header(self):
        """Generate Basic Auth header for token requests"""
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        return base64.b64encode(auth_bytes).decode('ascii')

    def generate_pkce_pair(self):
        """Generate PKCE code verifier and challenge for OAuth 2.0"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode('utf-8')).digest()).decode('utf-8').rstrip('=')
        return code_verifier, code_challenge

    def authorize(self):
        """Perform OAuth 2.0 authorization flow"""
        code_verifier, code_challenge = self.generate_pkce_pair()
        state = secrets.token_urlsafe(32)

        # Build authorization URL
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'activity heartrate sleep profile respiratory_rate oxygen_saturation cardio_fitness weight',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'state': state
        }

        auth_url = f"{AUTH_URL}?{urlencode(params)}"

        print("Opening browser for Fitbit authorization...")
        print(f"If browser doesn't open, visit: {auth_url}")
        webbrowser.open(auth_url)

        # Get authorization code from user
        redirect_response = input("\nPaste the full redirect URL here (after clicking Allow): ").strip()

        # Parse authorization code from redirect
        parsed_url = urlparse(redirect_response)
        query_params = parse_qs(parsed_url.query)

        if 'code' not in query_params:
            raise Exception("No authorization code found in redirect URL")

        auth_code = query_params['code'][0]

        # Exchange authorization code for access token
        token_data = {
            'client_id': self.client_id,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code': auth_code,
            'code_verifier': code_verifier
        }

        # Create Basic Auth header
        headers = {
            'Authorization': f'Basic {self._get_basic_auth_header()}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(TOKEN_URL, data=token_data, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")

        token_response = response.json()
        self.access_token = token_response['access_token']
        self.refresh_token = token_response['refresh_token']

        self.save_tokens(self.access_token, self.refresh_token)
        print("✓ Authorization successful!")

    def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        if not self.refresh_token:
            raise Exception("No refresh token available")

        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }

        headers = {
            'Authorization': f'Basic {self._get_basic_auth_header()}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(TOKEN_URL, data=token_data, headers=headers)

        if response.status_code == 200:
            token_response = response.json()
            self.access_token = token_response['access_token']
            self.refresh_token = token_response['refresh_token']
            self.save_tokens(self.access_token, self.refresh_token)
            print("✓ Token refreshed successfully")
        else:
            print(f"Token refresh failed: {response.status_code}")
            return False

        return True

    def make_api_request(self, endpoint, date=None):
        """Make authenticated API request to Fitbit"""
        if not self.access_token:
            raise Exception("No access token available. Please authorize first.")

        if date:
            endpoint = endpoint.replace('{date}', date.strftime('%Y-%m-%d'))

        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }

        response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers)

        if response.status_code == 401:
            print("Access token expired, refreshing...")
            if self.refresh_access_token():
                headers['Authorization'] = f'Bearer {self.access_token}'
                response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers)
            else:
                raise Exception("Failed to refresh token")

        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")

        return response.json()

    def get_daily_activity(self, date):
        """Get daily activity summary (steps, calories, distance, etc.)"""
        return self.make_api_request('/user/-/activities/date/{date}.json', date)

    def get_heart_rate(self, date):
        """Get heart rate data for a specific date"""
        return self.make_api_request('/user/-/activities/heart/date/{date}/1d.json', date)

    def get_sleep_data(self, date):
        """Get sleep data for a specific date"""
        return self.make_api_request('/user/-/sleep/date/{date}.json', date)

    def get_exercise_log(self, date):
        """Get exercise log for a specific date"""
        activity_data = self.get_daily_activity(date)
        return activity_data.get('activities', [])

    def get_hrv_data(self, date):
        """Get heart rate variability data for a specific date"""
        return self.make_api_request('/user/-/hrv/date/{date}.json', date)

    def get_spo2_data(self, date):
        """Get SpO2 (blood oxygen) data for a specific date"""
        return self.make_api_request('/user/-/spo2/date/{date}.json', date)

    def get_breathing_rate(self, date):
        """Get breathing rate data for a specific date"""
        return self.make_api_request('/user/-/br/date/{date}.json', date)

    def get_vo2_max(self, date):
        """Get VO2 Max (cardio fitness) data for a specific date"""
        return self.make_api_request('/user/-/cardioscore/date/{date}.json', date)

    def get_body_weight(self, date):
        """Get body weight log for a specific date (includes BMI and body fat if logged by scale)"""
        return self.make_api_request('/user/-/body/log/weight/date/{date}.json', date)

    def get_body_fat(self, date):
        """Get body fat percentage log for a specific date"""
        return self.make_api_request('/user/-/body/log/fat/date/{date}.json', date)

    def get_activity_tcx(self, log_id):
        """Get TCX data for a specific activity (GPS/heart rate data)"""
        endpoint = f'/user/-/activities/{log_id}.tcx'
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        }

        response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers)

        if response.status_code == 401:
            print("Access token expired, refreshing...")
            if self.refresh_access_token():
                headers['Authorization'] = f'Bearer {self.access_token}'
                response = requests.get(f"{API_BASE_URL}{endpoint}", headers=headers)
            else:
                raise Exception("Failed to refresh token")

        if response.status_code == 200:
            return response.text  # Return raw TCX XML
        elif response.status_code == 404:
            return None  # No TCX data available for this activity
        else:
            raise Exception(f"TCX request failed: {response.status_code} - {response.text}")

    def parse_tcx_data(self, tcx_xml, exercise_log_id):
        """Parse TCX XML and extract GPS points and route data"""
        if not tcx_xml:
            return [], None

        try:
            # Parse XML with namespace handling
            root = ET.fromstring(tcx_xml)

            # TCX namespace
            ns = {'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}

            gps_points = []
            route_data = {
                'exercise_log_id': exercise_log_id,
                'gps_points_count': 0,
                'total_distance_miles': 0,
                'total_elevation_gain_feet': 0,
                'start_latitude': None,
                'start_longitude': None,
                'end_latitude': None,
                'end_longitude': None,
                'min_latitude': None,
                'max_latitude': None,
                'min_longitude': None,
                'max_longitude': None,
                'max_speed_mph': 0
            }

            # Find all trackpoints
            trackpoints = root.findall('.//tcx:Trackpoint', ns)

            if not trackpoints:
                return [], None

            start_time = None
            elevations = []
            speeds = []
            latitudes = []
            longitudes = []

            for i, trackpoint in enumerate(trackpoints):
                # Time
                time_elem = trackpoint.find('tcx:Time', ns)
                if time_elem is not None:
                    point_time = datetime.fromisoformat(time_elem.text.replace('Z', '+00:00'))
                    if start_time is None:
                        start_time = point_time
                    time_offset = int((point_time - start_time).total_seconds())
                else:
                    time_offset = i * 30  # Estimate 30-second intervals

                # Position (GPS)
                position = trackpoint.find('tcx:Position', ns)
                latitude = longitude = None
                if position is not None:
                    lat_elem = position.find('tcx:LatitudeDegrees', ns)
                    lng_elem = position.find('tcx:LongitudeDegrees', ns)
                    if lat_elem is not None and lng_elem is not None:
                        latitude = float(lat_elem.text)
                        longitude = float(lng_elem.text)
                        latitudes.append(latitude)
                        longitudes.append(longitude)

                # Altitude
                altitude_elem = trackpoint.find('tcx:AltitudeMeters', ns)
                altitude_feet = None
                if altitude_elem is not None:
                    altitude_meters = float(altitude_elem.text)
                    altitude_feet = altitude_meters * 3.28084  # Convert to feet
                    elevations.append(altitude_feet)

                # Distance
                distance_elem = trackpoint.find('tcx:DistanceMeters', ns)
                distance_miles = None
                if distance_elem is not None:
                    distance_meters = float(distance_elem.text)
                    distance_miles = distance_meters * 0.000621371  # Convert to miles

                # Heart Rate
                hr_elem = trackpoint.find('.//tcx:Value', ns)
                heart_rate = None
                if hr_elem is not None:
                    try:
                        heart_rate = int(hr_elem.text)
                    except ValueError:
                        pass

                # Cadence
                cadence_elem = trackpoint.find('tcx:Cadence', ns)
                cadence = None
                if cadence_elem is not None:
                    try:
                        cadence = int(cadence_elem.text)
                    except ValueError:
                        pass

                # Speed (calculate from distance if available)
                speed_mph = None
                if i > 0 and distance_miles is not None:
                    prev_distance = gps_points[i-1]['distance_miles'] if gps_points else 0
                    prev_time = gps_points[i-1]['time_offset_seconds'] if gps_points else 0

                    if distance_miles > prev_distance and time_offset > prev_time:
                        time_diff_hours = (time_offset - prev_time) / 3600
                        distance_diff = distance_miles - prev_distance
                        speed_mph = distance_diff / time_diff_hours if time_diff_hours > 0 else 0
                        speeds.append(speed_mph)

                # Create GPS point
                gps_point = {
                    'exercise_log_id': exercise_log_id,
                    'time_offset_seconds': time_offset,
                    'latitude': latitude,
                    'longitude': longitude,
                    'altitude_feet': altitude_feet,
                    'distance_miles': distance_miles,
                    'heart_rate': heart_rate,
                    'cadence': cadence,
                    'speed_mph': speed_mph,
                    'recorded_at': point_time if time_elem is not None else None
                }

                gps_points.append(gps_point)

            # Calculate route summary
            if latitudes and longitudes:
                route_data.update({
                    'gps_points_count': len(gps_points),
                    'start_latitude': latitudes[0],
                    'start_longitude': longitudes[0],
                    'end_latitude': latitudes[-1],
                    'end_longitude': longitudes[-1],
                    'min_latitude': min(latitudes),
                    'max_latitude': max(latitudes),
                    'min_longitude': min(longitudes),
                    'max_longitude': max(longitudes)
                })

            if gps_points:
                # Total distance
                final_point = gps_points[-1]
                if final_point['distance_miles']:
                    route_data['total_distance_miles'] = final_point['distance_miles']

                # Elevation gain
                if elevations and len(elevations) > 1:
                    elevation_gain = sum(max(0, elevations[i] - elevations[i-1])
                                       for i in range(1, len(elevations)))
                    route_data['total_elevation_gain_feet'] = elevation_gain

                # Max speed
                if speeds:
                    route_data['max_speed_mph'] = max(speeds)

            return gps_points, route_data

        except ET.ParseError as e:
            print(f"Error parsing TCX data: {e}")
            return [], None
        except Exception as e:
            print(f"Error processing TCX data: {e}")
            return [], None

def save_to_database(fitbit_data, date, conn):
    """Save Fitbit data to Neon Postgres database

    Args:
        fitbit_data: Dictionary containing Fitbit API data
        date: Date for the data
        conn: Active psycopg2 connection (will not be closed by this function)
    """
    cur = conn.cursor()

    try:
        # Save daily activity data
        if 'activity' in fitbit_data and 'summary' in fitbit_data['activity']:
            summary = fitbit_data['activity']['summary']
            cur.execute("""
                INSERT INTO fitbit_activity_daily
                (date, steps, distance, calories_burned, active_minutes,
                 sedentary_minutes, lightly_active_minutes, fairly_active_minutes,
                 very_active_minutes, floors, elevation, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (date) DO UPDATE SET
                    steps = EXCLUDED.steps,
                    distance = EXCLUDED.distance,
                    calories_burned = EXCLUDED.calories_burned,
                    active_minutes = EXCLUDED.active_minutes,
                    sedentary_minutes = EXCLUDED.sedentary_minutes,
                    lightly_active_minutes = EXCLUDED.lightly_active_minutes,
                    fairly_active_minutes = EXCLUDED.fairly_active_minutes,
                    very_active_minutes = EXCLUDED.very_active_minutes,
                    floors = EXCLUDED.floors,
                    elevation = EXCLUDED.elevation,
                    updated_at = NOW()
            """, (
                date,
                summary.get('steps', 0),
                summary.get('distances', [{}])[0].get('distance', 0) if summary.get('distances') else 0,
                summary.get('caloriesOut', 0),
                summary.get('veryActiveMinutes', 0) + summary.get('fairlyActiveMinutes', 0),
                summary.get('sedentaryMinutes', 0),
                summary.get('lightlyActiveMinutes', 0),
                summary.get('fairlyActiveMinutes', 0),
                summary.get('veryActiveMinutes', 0),
                summary.get('floors', 0),
                summary.get('elevation', 0)
            ))
            print(f"✓ Saved activity data for {date}")

        # Save heart rate data
        if 'heart_rate' in fitbit_data:
            hr_data = fitbit_data['heart_rate']
            if hr_data.get('activities-heart'):
                hr_summary = hr_data['activities-heart'][0]
                resting_hr = hr_summary.get('value', {}).get('restingHeartRate')

                # Heart rate zones
                zones = hr_summary.get('value', {}).get('heartRateZones', [])
                out_of_range = next((z.get('minutes', 0) for z in zones if z.get('name') == 'Out of Range'), 0)
                fat_burn = next((z.get('minutes', 0) for z in zones if z.get('name') == 'Fat Burn'), 0)
                cardio = next((z.get('minutes', 0) for z in zones if z.get('name') == 'Cardio'), 0)
                peak = next((z.get('minutes', 0) for z in zones if z.get('name') == 'Peak'), 0)

                cur.execute("""
                    INSERT INTO fitbit_heart_rate
                    (date, resting_heart_rate, out_of_range_minutes, fat_burn_minutes,
                     cardio_minutes, peak_minutes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date) DO UPDATE SET
                        resting_heart_rate = EXCLUDED.resting_heart_rate,
                        out_of_range_minutes = EXCLUDED.out_of_range_minutes,
                        fat_burn_minutes = EXCLUDED.fat_burn_minutes,
                        cardio_minutes = EXCLUDED.cardio_minutes,
                        peak_minutes = EXCLUDED.peak_minutes
                """, (date, resting_hr, out_of_range, fat_burn, cardio, peak))
                print(f"✓ Saved heart rate data for {date}")

        # Save HRV data
        if 'hrv' in fitbit_data:
            hrv_data = fitbit_data['hrv']
            if hrv_data.get('hrv'):
                for hrv_entry in hrv_data['hrv']:
                    hrv_summary = hrv_entry.get('value', {})
                    daily_rmssd = hrv_summary.get('dailyRmssd')
                    deep_rmssd = hrv_summary.get('deepRmssd')

                    if daily_rmssd or deep_rmssd:
                        cur.execute("""
                            INSERT INTO fitbit_hrv
                            (date, daily_rmssd, deep_rmssd)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (date) DO UPDATE SET
                                daily_rmssd = EXCLUDED.daily_rmssd,
                                deep_rmssd = EXCLUDED.deep_rmssd
                        """, (date, daily_rmssd, deep_rmssd))
                        print(f"✓ Saved HRV data for {date}")

        # Save SpO2 data
        if 'spo2' in fitbit_data:
            spo2_data = fitbit_data['spo2']
            if spo2_data:
                spo2_value = spo2_data.get('value', {})
                avg_spo2 = spo2_value.get('avg')
                min_spo2 = spo2_value.get('min')
                max_spo2 = spo2_value.get('max')

                if avg_spo2:
                    cur.execute("""
                        INSERT INTO fitbit_spo2
                        (date, avg_spo2, min_spo2, max_spo2)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (date) DO UPDATE SET
                            avg_spo2 = EXCLUDED.avg_spo2,
                            min_spo2 = EXCLUDED.min_spo2,
                            max_spo2 = EXCLUDED.max_spo2
                    """, (date, avg_spo2, min_spo2, max_spo2))
                    print(f"✓ Saved SpO2 data for {date}")

        # Save Breathing Rate data
        if 'breathing_rate' in fitbit_data:
            br_data = fitbit_data['breathing_rate']
            if br_data.get('br'):
                for br_entry in br_data['br']:
                    br_value = br_entry.get('value', {})
                    breathing_rate = br_value.get('breathingRate')

                    if breathing_rate:
                        cur.execute("""
                            INSERT INTO fitbit_breathing_rate
                            (date, breaths_per_minute)
                            VALUES (%s, %s)
                            ON CONFLICT (date) DO UPDATE SET
                                breaths_per_minute = EXCLUDED.breaths_per_minute
                        """, (date, breathing_rate))
                        print(f"✓ Saved breathing rate data for {date}")

        # Save VO2 Max data
        if 'vo2_max' in fitbit_data:
            vo2_data = fitbit_data['vo2_max']
            if vo2_data.get('cardioScore'):
                for vo2_entry in vo2_data['cardioScore']:
                    vo2_value = vo2_entry.get('value', {})
                    vo2_max_raw = vo2_value.get('vo2Max')

                    if vo2_max_raw:
                        # Handle range format like "43-47" - take the midpoint
                        if isinstance(vo2_max_raw, str) and '-' in vo2_max_raw:
                            try:
                                parts = vo2_max_raw.split('-')
                                vo2_max = (float(parts[0]) + float(parts[1])) / 2
                            except (ValueError, IndexError):
                                print(f"  ⚠ Could not parse VO2 Max range: {vo2_max_raw}")
                                continue
                        else:
                            vo2_max = float(vo2_max_raw)

                        cur.execute("""
                            INSERT INTO fitbit_vo2_max
                            (date, vo2_max)
                            VALUES (%s, %s)
                            ON CONFLICT (date) DO UPDATE SET
                                vo2_max = EXCLUDED.vo2_max
                        """, (date, vo2_max))
                        print(f"✓ Saved VO2 Max data for {date} (VO2: {vo2_max})")

        # Save body metrics (weight, BMI, body fat) from Renpho scale via Fitbit
        if 'body_weight' in fitbit_data:
            weight_data = fitbit_data['body_weight']
            for entry in weight_data.get('weight', []):
                log_id = entry.get('logId')
                weight_raw = entry.get('weight')  # Fitbit returns kg when account is set to metric
                # Convert kg -> lbs (1 kg = 2.20462 lbs)
                weight_lbs = round(weight_raw * 2.20462, 2) if weight_raw else None
                bmi = entry.get('bmi')
                body_fat_pct = entry.get('fat')  # Scale sends this if supported
                source = entry.get('source', 'API')
                logged_time = entry.get('time')

                if weight_lbs:
                    cur.execute("""
                        INSERT INTO fitbit_body_metrics
                        (date, log_id, weight_lbs, bmi, body_fat_pct, source, logged_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (log_id) DO UPDATE SET
                            weight_lbs = EXCLUDED.weight_lbs,
                            bmi = EXCLUDED.bmi,
                            body_fat_pct = EXCLUDED.body_fat_pct,
                            source = EXCLUDED.source
                    """, (date, log_id, weight_lbs, bmi, body_fat_pct, source, logged_time))
            entries = weight_data.get('weight', [])
            if entries:
                latest = entries[-1]
                w_raw = latest.get('weight')
                w_lbs = round(w_raw * 2.20462, 2) if w_raw else None
                print(f"✓ Saved body metrics for {date}: {w_lbs} lbs ({w_raw} kg), BMI {latest.get('bmi')}, Fat {latest.get('fat')}%")

        # Save sleep data
        if 'sleep' in fitbit_data:
            sleep_data = fitbit_data['sleep']
            if sleep_data.get('sleep'):
                for sleep_log in sleep_data['sleep']:
                    cur.execute("""
                        INSERT INTO fitbit_sleep
                        (date, sleep_log_id, start_time, end_time, duration_minutes,
                         efficiency, minutes_asleep, minutes_awake, awake_count,
                         restless_count, restless_duration, time_in_bed)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (sleep_log_id) DO UPDATE SET
                            efficiency = EXCLUDED.efficiency,
                            minutes_asleep = EXCLUDED.minutes_asleep,
                            minutes_awake = EXCLUDED.minutes_awake,
                            awake_count = EXCLUDED.awake_count,
                            restless_count = EXCLUDED.restless_count,
                            restless_duration = EXCLUDED.restless_duration
                    """, (
                        date,
                        sleep_log.get('logId'),
                        sleep_log.get('startTime'),
                        sleep_log.get('endTime'),
                        sleep_log.get('duration', 0) // 60000,  # Convert ms to minutes
                        sleep_log.get('efficiency'),
                        sleep_log.get('minutesAsleep', 0),
                        sleep_log.get('minutesAwake', 0),
                        sleep_log.get('awakeCount', 0),
                        sleep_log.get('restlessCount', 0),
                        sleep_log.get('restlessDuration', 0) // 60000,  # Convert ms to minutes
                        sleep_log.get('timeInBed', 0)
                    ))
                print(f"✓ Saved sleep data for {date}")

        # Commit the successful data before trying exercises (which may fail)
        conn.commit()
        print(f"✓ Committed core data for {date}")

        # Save exercise logs with GPS data (in separate try/catch to avoid rolling back other data)
        try:
            if 'exercises' in fitbit_data:
                for exercise in fitbit_data['exercises']:
                    exercise_log_id = exercise.get('logId')
                    has_gps = exercise.get('hasGPS', False)
                    
                    # Parse start_time - could be full timestamp or just time string
                    start_time_raw = exercise.get('startTime')
                    start_time = None
                    if start_time_raw:
                        # If it's just a time like "07:34", combine with date
                        if len(start_time_raw) <= 8 and ':' in start_time_raw:
                            start_time = f"{date} {start_time_raw}"
                        else:
                            start_time = start_time_raw

                    # Save exercise log
                    cur.execute("""
                        INSERT INTO fitbit_exercises
                        (date, exercise_log_id, activity_name, activity_type_id,
                         duration_minutes, calories, distance, start_time, has_gps)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (exercise_log_id) DO UPDATE SET
                            duration_minutes = EXCLUDED.duration_minutes,
                            calories = EXCLUDED.calories,
                            distance = EXCLUDED.distance,
                            has_gps = EXCLUDED.has_gps
                    """, (
                        date,
                        exercise_log_id,
                        exercise.get('activityName'),
                        exercise.get('activityTypeId'),
                        exercise.get('duration', 0) // 60000,  # Convert ms to minutes
                        exercise.get('calories', 0),
                        exercise.get('distance', 0),
                        start_time,
                        has_gps
                    ))

                    # Save GPS points if available (must be inside the for loop)
                    gps_points = exercise.get('gps_points', [])
                    if gps_points:
                        # Clear existing GPS points for this exercise
                        cur.execute("DELETE FROM fitbit_gps_points WHERE exercise_log_id = %s", (exercise_log_id,))

                        # Batch insert GPS points using execute_values for better performance
                        gps_values = [
                            (
                                point['exercise_log_id'],
                                point['time_offset_seconds'],
                                point['latitude'],
                                point['longitude'],
                                point['altitude_feet'],
                                point['distance_miles'],
                                point['heart_rate'],
                                point['cadence'],
                                point['speed_mph'],
                                point['recorded_at']
                            )
                            for point in gps_points
                        ]
                        execute_values(cur, """
                            INSERT INTO fitbit_gps_points
                            (exercise_log_id, time_offset_seconds, latitude, longitude,
                             altitude_feet, distance_miles, heart_rate, cadence,
                             speed_mph, recorded_at)
                            VALUES %s
                        """, gps_values)

                    # Save route summary if available
                    route_data = exercise.get('route_data')
                    if route_data and route_data['gps_points_count'] > 0:
                        cur.execute("""
                            INSERT INTO fitbit_routes
                            (exercise_log_id, activity_name, start_latitude, start_longitude,
                             end_latitude, end_longitude, min_latitude, max_latitude,
                             min_longitude, max_longitude, total_distance_miles,
                             total_elevation_gain_feet, max_speed_mph, gps_points_count, route_date)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (exercise_log_id) DO UPDATE SET
                                start_latitude = EXCLUDED.start_latitude,
                                start_longitude = EXCLUDED.start_longitude,
                                end_latitude = EXCLUDED.end_latitude,
                                end_longitude = EXCLUDED.end_longitude,
                                min_latitude = EXCLUDED.min_latitude,
                                max_latitude = EXCLUDED.max_latitude,
                                min_longitude = EXCLUDED.min_longitude,
                                max_longitude = EXCLUDED.max_longitude,
                                total_distance_miles = EXCLUDED.total_distance_miles,
                                total_elevation_gain_feet = EXCLUDED.total_elevation_gain_feet,
                                max_speed_mph = EXCLUDED.max_speed_mph,
                                gps_points_count = EXCLUDED.gps_points_count
                        """, (
                            route_data['exercise_log_id'],
                            exercise.get('activityName'),
                            route_data['start_latitude'],
                            route_data['start_longitude'],
                            route_data['end_latitude'],
                            route_data['end_longitude'],
                            route_data['min_latitude'],
                            route_data['max_latitude'],
                            route_data['min_longitude'],
                            route_data['max_longitude'],
                            route_data['total_distance_miles'],
                            route_data['total_elevation_gain_feet'],
                            route_data['max_speed_mph'],
                            route_data['gps_points_count'],
                            date
                        ))

                print(f"✓ Saved {len(fitbit_data['exercises'])} exercise logs for {date}")
        except Exception as e:
            print(f"✗ Exercise data error for {date}: {e}")
            # Don't rollback - core data already committed

        # Final commit for any remaining changes
        conn.commit()

    except Exception as e:
        print(f"✗ Database error for {date}: {e}")
        conn.rollback()
    finally:
        cur.close()

def create_tables_if_needed(db_conn):
    """Create Fitbit tables if they don't exist"""
    conn = psycopg2.connect(db_conn)
    cur = conn.cursor()

    try:
        # Read and execute schema
        schema_sql = """
        -- Daily activity summary (steps, calories, distance, etc.)
        CREATE TABLE IF NOT EXISTS fitbit_activity_daily (
          id SERIAL PRIMARY KEY,
          date DATE NOT NULL UNIQUE,
          steps INTEGER,
          distance DECIMAL(8,2),
          calories_burned INTEGER,
          active_minutes INTEGER,
          sedentary_minutes INTEGER,
          lightly_active_minutes INTEGER,
          fairly_active_minutes INTEGER,
          very_active_minutes INTEGER,
          floors INTEGER,
          elevation DECIMAL(8,2),
          created_at TIMESTAMP DEFAULT NOW(),
          updated_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fitbit_heart_rate (
          id SERIAL PRIMARY KEY,
          date DATE NOT NULL UNIQUE,
          resting_heart_rate INTEGER,
          out_of_range_minutes INTEGER,
          fat_burn_minutes INTEGER,
          cardio_minutes INTEGER,
          peak_minutes INTEGER,
          created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fitbit_hrv (
          id SERIAL PRIMARY KEY,
          date DATE NOT NULL UNIQUE,
          daily_rmssd DECIMAL(6,2),
          deep_rmssd DECIMAL(6,2),
          created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fitbit_spo2 (
          id SERIAL PRIMARY KEY,
          date DATE NOT NULL UNIQUE,
          avg_spo2 DECIMAL(5,2),
          min_spo2 DECIMAL(5,2),
          max_spo2 DECIMAL(5,2),
          created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fitbit_breathing_rate (
          id SERIAL PRIMARY KEY,
          date DATE NOT NULL UNIQUE,
          breaths_per_minute DECIMAL(5,2),
          created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fitbit_vo2_max (
          id SERIAL PRIMARY KEY,
          date DATE NOT NULL UNIQUE,
          vo2_max DECIMAL(5,2),
          created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fitbit_sleep (
          id SERIAL PRIMARY KEY,
          date DATE NOT NULL,
          sleep_log_id BIGINT UNIQUE,
          start_time TIMESTAMP,
          end_time TIMESTAMP,
          duration_minutes INTEGER,
          efficiency INTEGER,
          minutes_asleep INTEGER,
          minutes_awake INTEGER,
          awake_count INTEGER,
          restless_count INTEGER,
          restless_duration INTEGER,
          time_in_bed INTEGER,
          created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fitbit_exercises (
          id SERIAL PRIMARY KEY,
          date DATE NOT NULL,
          exercise_log_id BIGINT UNIQUE,
          activity_name VARCHAR(100),
          activity_type_id INTEGER,
          duration_minutes INTEGER,
          calories INTEGER,
          distance DECIMAL(8,2),
          pace DECIMAL(8,2),
          speed DECIMAL(8,2),
          heart_rate_avg INTEGER,
          heart_rate_max INTEGER,
          start_time TIMESTAMP,
          has_gps BOOLEAN DEFAULT FALSE,
          created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fitbit_gps_points (
          id SERIAL PRIMARY KEY,
          exercise_log_id BIGINT REFERENCES fitbit_exercises(exercise_log_id) ON DELETE CASCADE,
          time_offset_seconds INTEGER,
          latitude DECIMAL(10,8),
          longitude DECIMAL(11,8),
          altitude_feet DECIMAL(8,2),
          distance_miles DECIMAL(8,3),
          heart_rate INTEGER,
          cadence INTEGER,
          speed_mph DECIMAL(6,3),
          recorded_at TIMESTAMP,
          created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fitbit_routes (
          id SERIAL PRIMARY KEY,
          exercise_log_id BIGINT REFERENCES fitbit_exercises(exercise_log_id) ON DELETE CASCADE,
          activity_name VARCHAR(100),
          start_latitude DECIMAL(10,8),
          start_longitude DECIMAL(11,8),
          end_latitude DECIMAL(10,8),
          end_longitude DECIMAL(11,8),
          min_latitude DECIMAL(10,8),
          max_latitude DECIMAL(10,8),
          min_longitude DECIMAL(11,8),
          max_longitude DECIMAL(11,8),
          total_distance_miles DECIMAL(8,3),
          total_elevation_gain_feet DECIMAL(8,2),
          avg_pace_min_per_mile DECIMAL(6,2),
          max_speed_mph DECIMAL(6,3),
          gps_points_count INTEGER,
          route_date DATE,
          created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS fitbit_body_metrics (
          id SERIAL PRIMARY KEY,
          date DATE NOT NULL,
          log_id BIGINT UNIQUE,
          weight_lbs DECIMAL(6,2),
          bmi DECIMAL(5,2),
          body_fat_pct DECIMAL(5,2),
          source VARCHAR(50),
          logged_time TIME,
          created_at TIMESTAMP DEFAULT NOW()
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_fitbit_activity_date ON fitbit_activity_daily(date);
        CREATE INDEX IF NOT EXISTS idx_fitbit_heart_rate_date ON fitbit_heart_rate(date);
        CREATE INDEX IF NOT EXISTS idx_fitbit_hrv_date ON fitbit_hrv(date);
        CREATE INDEX IF NOT EXISTS idx_fitbit_spo2_date ON fitbit_spo2(date);
        CREATE INDEX IF NOT EXISTS idx_fitbit_breathing_rate_date ON fitbit_breathing_rate(date);
        CREATE INDEX IF NOT EXISTS idx_fitbit_vo2_max_date ON fitbit_vo2_max(date);
        CREATE INDEX IF NOT EXISTS idx_fitbit_sleep_date ON fitbit_sleep(date);
        CREATE INDEX IF NOT EXISTS idx_fitbit_exercises_date ON fitbit_exercises(date);
        CREATE INDEX IF NOT EXISTS idx_fitbit_gps_points_exercise ON fitbit_gps_points(exercise_log_id);
        CREATE INDEX IF NOT EXISTS idx_fitbit_routes_date ON fitbit_routes(route_date);
        """

        cur.execute(schema_sql)
        conn.commit()
        print("✓ Database tables ready")

    except Exception as e:
        print(f"⚠ Database setup warning: {e}")
    finally:
        cur.close()
        conn.close()

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Sync Fitbit data to Postgres database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Default: sync last 3 days
  python fitbit_integration.py

  # Sync last 7 days
  python fitbit_integration.py --days 7

  # Sync specific date range
  python fitbit_integration.py --start-date 2025-01-01 --end-date 2025-01-15

  # Backfill entire month
  python fitbit_integration.py --start-date 2024-12-01 --end-date 2024-12-31
        '''
    )
    parser.add_argument(
        '--days',
        type=int,
        default=3,
        help='Number of days to sync back from today (default: 3)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date for sync (YYYY-MM-DD). Overrides --days if provided.'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for sync (YYYY-MM-DD). Defaults to today if --start-date is provided.'
    )
    args = parser.parse_args()

    print("=== Fitbit Data Sync ===\n")

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

    # Determine date range based on arguments
    if args.start_date:
        # Use explicit date range
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
            if args.end_date:
                end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
            else:
                end_date = datetime.now().date()
        except ValueError as e:
            print(f"❌ Invalid date format: {e}")
            print("Use YYYY-MM-DD format (e.g., 2025-01-15)")
            return
    else:
        # Use days-back approach (default behavior)
        end_date = datetime.now().date()
        # 3-day lookback optimized for daily automated runs:
        # - API safe: ~24-30 calls vs 150/hour limit
        # - Redundancy: Can miss 1-2 runs without data loss due to overlap
        # - Catches late data: Fitbit sometimes processes sleep/activity data with delay
        # - UPSERT safe: Database handles duplicate dates gracefully
        days_back = args.days
        start_date = end_date - timedelta(days=days_back-1)

    # Calculate total days for display
    total_range_days = (end_date - start_date).days + 1
    print(f"\nSyncing Fitbit data from {start_date} to {end_date} ({total_range_days} days)...")

    # Create persistent database connection for entire sync
    conn = psycopg2.connect(db_conn)

    try:
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

                # Body weight / BMI / body fat (from Renpho scale via Fitbit)
                try:
                    body_weight_data = fitbit.get_body_weight(current_date)
                    fitbit_data['body_weight'] = body_weight_data
                    entries = body_weight_data.get('weight', [])
                    if entries:
                        latest = entries[-1]
                        w_raw = latest.get('weight')
                        w_lbs = round(w_raw * 2.20462, 2) if w_raw else None
                        print(f"  ✓ Body weight: {w_lbs} lbs ({w_raw} kg), BMI {latest.get('bmi')}, Fat {latest.get('fat')}%")
                    else:
                        print(f"  - Body weight: No measurement logged")
                except Exception as e:
                    print(f"  ✗ Body weight data error: {e}")

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
                    save_to_database(fitbit_data, current_date, conn)
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

    finally:
        conn.close()
        print("✓ Database connection closed")

if __name__ == "__main__":
    main()