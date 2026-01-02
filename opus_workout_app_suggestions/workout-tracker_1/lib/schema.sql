-- Workout Tracker Database Schema
-- Run this in your Neon console to set up the database

-- Exercises reference table (populated from free-exercise-db + custom)
CREATE TABLE IF NOT EXISTS exercises (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  category VARCHAR(50), -- strength, cardio, stretching, etc.
  equipment VARCHAR(100),
  primary_muscles TEXT[], -- array of muscle names
  secondary_muscles TEXT[],
  instructions TEXT,
  is_custom BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Workout routines (Upper A, Lower B, etc.)
CREATE TABLE IF NOT EXISTS routines (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL, -- "Upper A (Push)"
  description TEXT,
  day_order INT, -- 1, 2, 3, 4 for ordering
  created_at TIMESTAMP DEFAULT NOW()
);

-- Exercises within each routine (with target sets/reps)
CREATE TABLE IF NOT EXISTS routine_exercises (
  id SERIAL PRIMARY KEY,
  routine_id INT REFERENCES routines(id) ON DELETE CASCADE,
  exercise_id INT REFERENCES exercises(id),
  exercise_order INT NOT NULL, -- order within routine
  target_sets INT DEFAULT 3,
  target_reps VARCHAR(20) DEFAULT '8-10', -- "8-10" or "1 min" for planks
  notes TEXT,
  UNIQUE(routine_id, exercise_id)
);

-- Logged workouts (each time you complete a routine)
CREATE TABLE IF NOT EXISTS workout_logs (
  id SERIAL PRIMARY KEY,
  routine_id INT REFERENCES routines(id),
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP,
  notes TEXT
);

-- Individual sets within a workout
CREATE TABLE IF NOT EXISTS workout_sets (
  id SERIAL PRIMARY KEY,
  workout_log_id INT REFERENCES workout_logs(id) ON DELETE CASCADE,
  exercise_id INT REFERENCES exercises(id),
  set_number INT NOT NULL,
  weight DECIMAL(6,2), -- in lbs or kg (your preference)
  reps INT,
  duration_seconds INT, -- for timed exercises like planks
  rpe INT CHECK (rpe >= 1 AND rpe <= 10), -- rate of perceived exertion
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Body weight tracking (can sync with FatSecret later)
CREATE TABLE IF NOT EXISTS weight_logs (
  id SERIAL PRIMARY KEY,
  weight DECIMAL(5,2) NOT NULL,
  logged_at DATE DEFAULT CURRENT_DATE,
  source VARCHAR(50) DEFAULT 'manual', -- 'manual' or 'fatsecret'
  notes TEXT
);

-- Indexes for common queries
CREATE INDEX idx_workout_logs_date ON workout_logs(started_at);
CREATE INDEX idx_workout_sets_log ON workout_sets(workout_log_id);
CREATE INDEX idx_weight_logs_date ON weight_logs(logged_at);
