-- Fitbit API Data Schema
-- Add these tables to your existing Neon database

-- Daily activity summary (steps, calories, distance, etc.)
CREATE TABLE IF NOT EXISTS fitbit_activity_daily (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL UNIQUE,
  steps INTEGER,
  distance DECIMAL(8,2), -- miles
  calories_burned INTEGER,
  active_minutes INTEGER,
  sedentary_minutes INTEGER,
  lightly_active_minutes INTEGER,
  fairly_active_minutes INTEGER,
  very_active_minutes INTEGER,
  floors INTEGER,
  elevation DECIMAL(8,2), -- feet
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Heart rate zones and resting heart rate
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

-- Heart Rate Variability (HRV) - recovery and stress indicator
CREATE TABLE IF NOT EXISTS fitbit_hrv (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL UNIQUE,
  daily_rmssd DECIMAL(6,2), -- Root Mean Square of Successive Differences (ms)
  deep_rmssd DECIMAL(6,2), -- HRV during deep sleep (ms)
  created_at TIMESTAMP DEFAULT NOW()
);

-- Blood Oxygen Saturation (SpO2)
CREATE TABLE IF NOT EXISTS fitbit_spo2 (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL UNIQUE,
  avg_spo2 DECIMAL(5,2), -- Average SpO2 percentage
  min_spo2 DECIMAL(5,2), -- Minimum SpO2 percentage
  max_spo2 DECIMAL(5,2), -- Maximum SpO2 percentage
  created_at TIMESTAMP DEFAULT NOW()
);

-- Breathing Rate (Respiratory Rate)
CREATE TABLE IF NOT EXISTS fitbit_breathing_rate (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL UNIQUE,
  breaths_per_minute DECIMAL(5,2), -- Average breaths per minute during sleep
  created_at TIMESTAMP DEFAULT NOW()
);

-- VO2 Max (Cardio Fitness Score)
CREATE TABLE IF NOT EXISTS fitbit_vo2_max (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL UNIQUE,
  vo2_max DECIMAL(5,2), -- VO2 Max value (ml/kg/min)
  created_at TIMESTAMP DEFAULT NOW()
);

-- Sleep data
CREATE TABLE IF NOT EXISTS fitbit_sleep (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  sleep_log_id BIGINT UNIQUE,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  duration_minutes INTEGER,
  efficiency INTEGER, -- percentage
  minutes_asleep INTEGER,
  minutes_awake INTEGER,
  awake_count INTEGER,
  restless_count INTEGER,
  restless_duration INTEGER,
  time_in_bed INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Exercise/workout sessions from Fitbit
CREATE TABLE IF NOT EXISTS fitbit_exercises (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  exercise_log_id BIGINT UNIQUE,
  activity_name VARCHAR(100),
  activity_type_id INTEGER,
  duration_minutes INTEGER,
  calories INTEGER,
  distance DECIMAL(8,2),
  pace DECIMAL(8,2), -- minutes per mile
  speed DECIMAL(8,2), -- mph
  heart_rate_avg INTEGER,
  heart_rate_max INTEGER,
  start_time TIMESTAMP,
  has_gps BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Body metrics from smart scale (Renpho → Fitbit sync)
CREATE TABLE IF NOT EXISTS fitbit_body_metrics (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,
  log_id BIGINT UNIQUE,
  weight_lbs DECIMAL(6,2),       -- body weight in lbs
  bmi DECIMAL(5,2),              -- body mass index
  body_fat_pct DECIMAL(5,2),     -- body fat percentage (from scale BIA)
  source VARCHAR(50),            -- 'Aria', 'Renpho', 'API', etc.
  logged_time TIME,              -- time of measurement
  created_at TIMESTAMP DEFAULT NOW()
);

-- Separate table for raw TCX data (optional - only if you need it)
CREATE TABLE IF NOT EXISTS fitbit_exercise_tcx (
  exercise_log_id BIGINT PRIMARY KEY REFERENCES fitbit_exercises(exercise_log_id) ON DELETE CASCADE,
  tcx_data TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- GPS tracking points from TCX data
CREATE TABLE IF NOT EXISTS fitbit_gps_points (
  id SERIAL PRIMARY KEY,
  exercise_log_id BIGINT REFERENCES fitbit_exercises(exercise_log_id) ON DELETE CASCADE,
  time_offset_seconds INTEGER, -- seconds from start of exercise
  latitude DECIMAL(10,8), -- GPS latitude
  longitude DECIMAL(11,8), -- GPS longitude
  altitude_feet DECIMAL(8,2), -- elevation in feet
  distance_miles DECIMAL(8,3), -- cumulative distance from start
  heart_rate INTEGER, -- heart rate at this point
  cadence INTEGER, -- steps per minute
  speed_mph DECIMAL(6,3), -- instantaneous speed
  recorded_at TIMESTAMP, -- actual timestamp of GPS point
  created_at TIMESTAMP DEFAULT NOW()
);

-- Route summaries for mapping
CREATE TABLE IF NOT EXISTS fitbit_routes (
  id SERIAL PRIMARY KEY,
  exercise_log_id BIGINT REFERENCES fitbit_exercises(exercise_log_id) ON DELETE CASCADE,
  activity_name VARCHAR(100),
  start_latitude DECIMAL(10,8),
  start_longitude DECIMAL(11,8),
  end_latitude DECIMAL(10,8),
  end_longitude DECIMAL(11,8),
  min_latitude DECIMAL(10,8), -- bounding box
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

-- Add unique constraint on routes (prevent duplicates)
ALTER TABLE fitbit_routes ADD CONSTRAINT unique_route_exercise UNIQUE (exercise_log_id);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_fitbit_activity_date ON fitbit_activity_daily(date);
CREATE INDEX IF NOT EXISTS idx_fitbit_heart_rate_date ON fitbit_heart_rate(date);
CREATE INDEX IF NOT EXISTS idx_fitbit_hrv_date ON fitbit_hrv(date);
CREATE INDEX IF NOT EXISTS idx_fitbit_spo2_date ON fitbit_spo2(date);
CREATE INDEX IF NOT EXISTS idx_fitbit_breathing_rate_date ON fitbit_breathing_rate(date);
CREATE INDEX IF NOT EXISTS idx_fitbit_vo2_max_date ON fitbit_vo2_max(date);
CREATE INDEX IF NOT EXISTS idx_fitbit_sleep_date ON fitbit_sleep(date);
CREATE INDEX IF NOT EXISTS idx_fitbit_exercises_date ON fitbit_exercises(date);
CREATE INDEX IF NOT EXISTS idx_fitbit_gps_points_exercise ON fitbit_gps_points(exercise_log_id);
CREATE INDEX IF NOT EXISTS idx_fitbit_gps_points_time ON fitbit_gps_points(exercise_log_id, time_offset_seconds);
CREATE INDEX IF NOT EXISTS idx_fitbit_routes_date ON fitbit_routes(route_date);
CREATE INDEX IF NOT EXISTS idx_fitbit_routes_location ON fitbit_routes(start_latitude, start_longitude);
CREATE INDEX IF NOT EXISTS idx_fitbit_body_metrics_date ON fitbit_body_metrics(date);

-- Daily summary table for daily habits (Fitbit + FatSecret data)
CREATE TABLE IF NOT EXISTS daily_summary (
  date DATE PRIMARY KEY,
  -- Fitbit daily activity data
  steps INTEGER,
  distance_miles DECIMAL(8,2),
  calories_burned INTEGER,
  active_minutes INTEGER,
  resting_heart_rate INTEGER,
  sleep_duration_minutes INTEGER,
  sleep_efficiency INTEGER,
  -- Fitbit recovery & vitals
  hrv_rmssd DECIMAL(6,2), -- Heart rate variability
  spo2_avg DECIMAL(5,2), -- Blood oxygen percentage
  breathing_rate DECIMAL(5,2), -- Breaths per minute
  vo2_max DECIMAL(5,2), -- Cardio fitness score
  -- Body metrics (from Renpho scale via Fitbit)
  weight_lbs DECIMAL(6,2),
  bmi DECIMAL(5,2),
  body_fat_pct DECIMAL(5,2),
  -- FatSecret nutrition data (populated from diet_logs)
  calories_consumed INTEGER,
  protein_g DECIMAL(6,1),
  carbs_g DECIMAL(6,1),
  fat_g DECIMAL(6,1),
  -- Computed fields
  net_calories INTEGER, -- calories_consumed - calories_burned
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_summary_date ON daily_summary(date);