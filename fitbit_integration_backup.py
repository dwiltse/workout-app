#!/usr/bin/env python3
"""
Fitbit API Integration for Personal Health Data
Fetches steps, workouts, heart rate, and sleep data from Fitbit API
"""

import requests
import psycopg2
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
        print("✓ Saved Fitbit tokens to cache")

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
            'scope': 'activity heartrate sleep profile',
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
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        headers = {
            'Authorization': f'Basic {auth_b64}',
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

        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

        headers = {
            'Authorization': f'Basic {auth_b64}',
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

def save_to_database(fitbit_data, date, db_conn):
    """Save Fitbit data to Neon Postgres database"""
    conn = psycopg2.connect(db_conn)
    cur = conn.cursor()

    try:
        # Save daily activity data
        if 'summary' in fitbit_data['activity']:
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
                    tcx_data = exercise.get('tcx_data', '')

                    # Save exercise log
                    cur.execute("""
                        INSERT INTO fitbit_exercises
                        (date, exercise_log_id, activity_name, activity_type_id,
                         duration_minutes, calories, distance, start_time, has_gps, tcx_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (exercise_log_id) DO UPDATE SET
                            duration_minutes = EXCLUDED.duration_minutes,
                            calories = EXCLUDED.calories,
                            distance = EXCLUDED.distance,
                            has_gps = EXCLUDED.has_gps,
                            tcx_data = EXCLUDED.tcx_data
                    """, (
                        date,
                        exercise_log_id,
                        exercise.get('activityName'),
                        exercise.get('activityTypeId'),
                        exercise.get('duration', 0) // 60000,  # Convert ms to minutes
                        exercise.get('calories', 0),
                        exercise.get('distance', 0),
                        exercise.get('startTime'),
                        has_gps,
                        tcx_data
                    ))

                # Save GPS points if available
                gps_points = exercise.get('gps_points', [])
                if gps_points:
                    # Clear existing GPS points for this exercise
                    cur.execute("DELETE FROM fitbit_gps_points WHERE exercise_log_id = %s", (exercise_log_id,))

                    # Insert GPS points
                    for point in gps_points:
                        cur.execute("""
                            INSERT INTO fitbit_gps_points
                            (exercise_log_id, time_offset_seconds, latitude, longitude,
                             altitude_feet, distance_miles, heart_rate, cadence,
                             speed_mph, recorded_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
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
                        ))

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
        conn.close()

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
          tcx_data TEXT,
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

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_fitbit_activity_date ON fitbit_activity_daily(date);
        CREATE INDEX IF NOT EXISTS idx_fitbit_heart_rate_date ON fitbit_heart_rate(date);
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

    # Get date range to sync
    end_date = datetime.now().date()
    days_back = input(f"\nHow many days back to sync? [default: 7]: ").strip()
    days_back = int(days_back) if days_back.isdigit() else 7

    start_date = end_date - timedelta(days=days_back-1)

    print(f"\nSyncing Fitbit data from {start_date} to {end_date}...")

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