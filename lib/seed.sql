-- Seed data: Your Caliber routines
-- Run this AFTER schema.sql

-- Insert exercises (matching your Caliber screenshots)
INSERT INTO exercises (name, category, equipment, primary_muscles, secondary_muscles) VALUES
-- Upper A (Push)
('Dumbbell Incline Bench Press', 'strength', 'dumbbell', ARRAY['chest'], ARRAY['shoulders', 'triceps']),
('Dumbbell Shoulder Press', 'strength', 'dumbbell', ARRAY['shoulders'], ARRAY['triceps']),
('Push-Up', 'strength', 'bodyweight', ARRAY['chest'], ARRAY['shoulders', 'triceps']),
('Barbell Lying Tricep Extension', 'strength', 'barbell', ARRAY['triceps'], ARRAY[]::TEXT[]),
('Dumbbell Lateral Raise', 'strength', 'dumbbell', ARRAY['shoulders'], ARRAY[]::TEXT[]),
('Dumbbell Standing Preacher Curl', 'strength', 'dumbbell', ARRAY['biceps'], ARRAY['forearms']),

-- Lower A (Quad)
('Dumbbell Bulgarian Split Squat', 'strength', 'dumbbell', ARRAY['quadriceps', 'glutes'], ARRAY['hamstrings']),
('Dumbbell Step-Up', 'strength', 'dumbbell', ARRAY['quadriceps', 'glutes'], ARRAY[]::TEXT[]),
('Dumbbell Hip Thrust', 'strength', 'dumbbell', ARRAY['glutes'], ARRAY['hamstrings']),
('Dumbbell Single Leg Calf Raise', 'strength', 'dumbbell', ARRAY['calves'], ARRAY[]::TEXT[]),
('Hanging Knee Raise', 'strength', 'bodyweight', ARRAY['abdominals'], ARRAY['hip flexors']),

-- Upper B (Pull)
('Pull-Up', 'strength', 'bodyweight', ARRAY['lats', 'back'], ARRAY['biceps']),
('Dumbbell Bent-Over Row', 'strength', 'dumbbell', ARRAY['back', 'lats'], ARRAY['biceps']),
('Dumbbell Shrug', 'strength', 'dumbbell', ARRAY['traps'], ARRAY[]::TEXT[]),
('Ring Row', 'strength', 'rings', ARRAY['back'], ARRAY['biceps']),
('Dumbbell Incline Curl', 'strength', 'dumbbell', ARRAY['biceps'], ARRAY['forearms']),

-- Lower B (Hinge)
('Dumbbell Walking Lunge', 'strength', 'dumbbell', ARRAY['quadriceps', 'glutes'], ARRAY['hamstrings']),
('Dumbbell Single Leg Romanian Deadlift', 'strength', 'dumbbell', ARRAY['hamstrings', 'glutes'], ARRAY['lower back']),
('Russian Hamstring Curl', 'strength', 'bodyweight', ARRAY['hamstrings'], ARRAY[]::TEXT[]),
('Ab Wheel Kneeling Rollout', 'strength', 'ab wheel', ARRAY['abdominals'], ARRAY['shoulders']),
('Side Plank', 'strength', 'bodyweight', ARRAY['obliques', 'abdominals'], ARRAY[]::TEXT[])
ON CONFLICT (name) DO NOTHING;

-- Insert routines
INSERT INTO routines (name, description, day_order) VALUES
('Upper A (Push)', 'Push-focused upper body: chest, shoulders, triceps', 1),
('Lower A (Quad)', 'Quad-focused lower body: squats, lunges, hip thrust', 2),
('Upper B (Pull)', 'Pull-focused upper body: back, biceps, traps', 3),
('Lower B (Hinge)', 'Hinge-focused lower body: deadlifts, hamstrings, core', 4);

-- Link exercises to routines
-- Upper A (Push)
INSERT INTO routine_exercises (routine_id, exercise_id, exercise_order, target_sets, target_reps)
SELECT r.id, e.id, 
  CASE e.name
    WHEN 'Dumbbell Incline Bench Press' THEN 1
    WHEN 'Dumbbell Shoulder Press' THEN 2
    WHEN 'Push-Up' THEN 3
    WHEN 'Barbell Lying Tricep Extension' THEN 4
    WHEN 'Dumbbell Lateral Raise' THEN 5
    WHEN 'Dumbbell Standing Preacher Curl' THEN 6
  END,
  3, '8-10'
FROM routines r, exercises e
WHERE r.name = 'Upper A (Push)'
AND e.name IN ('Dumbbell Incline Bench Press', 'Dumbbell Shoulder Press', 'Push-Up', 
               'Barbell Lying Tricep Extension', 'Dumbbell Lateral Raise', 'Dumbbell Standing Preacher Curl');

-- Lower A (Quad)
INSERT INTO routine_exercises (routine_id, exercise_id, exercise_order, target_sets, target_reps)
SELECT r.id, e.id,
  CASE e.name
    WHEN 'Dumbbell Bulgarian Split Squat' THEN 1
    WHEN 'Dumbbell Step-Up' THEN 2
    WHEN 'Dumbbell Hip Thrust' THEN 3
    WHEN 'Dumbbell Single Leg Calf Raise' THEN 4
    WHEN 'Hanging Knee Raise' THEN 5
  END,
  3, '8-10'
FROM routines r, exercises e
WHERE r.name = 'Lower A (Quad)'
AND e.name IN ('Dumbbell Bulgarian Split Squat', 'Dumbbell Step-Up', 'Dumbbell Hip Thrust',
               'Dumbbell Single Leg Calf Raise', 'Hanging Knee Raise');

-- Upper B (Pull)
INSERT INTO routine_exercises (routine_id, exercise_id, exercise_order, target_sets, target_reps)
SELECT r.id, e.id,
  CASE e.name
    WHEN 'Pull-Up' THEN 1
    WHEN 'Dumbbell Bent-Over Row' THEN 2
    WHEN 'Dumbbell Shrug' THEN 3
    WHEN 'Ring Row' THEN 4
    WHEN 'Dumbbell Incline Curl' THEN 5
  END,
  3, '8-10'
FROM routines r, exercises e
WHERE r.name = 'Upper B (Pull)'
AND e.name IN ('Pull-Up', 'Dumbbell Bent-Over Row', 'Dumbbell Shrug', 'Ring Row', 'Dumbbell Incline Curl');

-- Lower B (Hinge)
INSERT INTO routine_exercises (routine_id, exercise_id, exercise_order, target_sets, target_reps)
SELECT r.id, e.id,
  CASE e.name
    WHEN 'Dumbbell Walking Lunge' THEN 1
    WHEN 'Dumbbell Single Leg Romanian Deadlift' THEN 2
    WHEN 'Russian Hamstring Curl' THEN 3
    WHEN 'Ab Wheel Kneeling Rollout' THEN 4
    WHEN 'Side Plank' THEN 5
  END,
  3,
  CASE WHEN e.name = 'Side Plank' THEN '1 min' ELSE '8-10' END
FROM routines r, exercises e
WHERE r.name = 'Lower B (Hinge)'
AND e.name IN ('Dumbbell Walking Lunge', 'Dumbbell Single Leg Romanian Deadlift', 
               'Russian Hamstring Curl', 'Ab Wheel Kneeling Rollout', 'Side Plank');
