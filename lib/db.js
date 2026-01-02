import { neon } from '@neondatabase/serverless';

// Create a SQL query function using your Neon connection string
// Set DATABASE_URL in your .env.local file
export const sql = neon(process.env.DATABASE_URL);

// Helper for common queries
export async function getRoutines() {
  return sql`
    SELECT r.*, 
      (SELECT COUNT(*) FROM routine_exercises WHERE routine_id = r.id) as exercise_count
    FROM routines r 
    ORDER BY day_order
  `;
}

export async function getRoutineWithExercises(routineId) {
  const routine = await sql`
    SELECT * FROM routines WHERE id = ${routineId}
  `;
  
  const exercises = await sql`
    SELECT re.*, e.name, e.primary_muscles, e.secondary_muscles, e.equipment
    FROM routine_exercises re
    JOIN exercises e ON e.id = re.exercise_id
    WHERE re.routine_id = ${routineId}
    ORDER BY re.exercise_order
  `;
  
  return { routine: routine[0], exercises };
}

export async function logWorkout(routineId) {
  const result = await sql`
    INSERT INTO workout_logs (routine_id, started_at)
    VALUES (${routineId}, NOW())
    RETURNING id
  `;
  return result[0].id;
}

export async function logSet(workoutLogId, exerciseId, setNumber, weight, reps, rpe = null) {
  return sql`
    INSERT INTO workout_sets (workout_log_id, exercise_id, set_number, weight, reps, rpe)
    VALUES (${workoutLogId}, ${exerciseId}, ${setNumber}, ${weight}, ${reps}, ${rpe})
    RETURNING id
  `;
}

export async function completeWorkout(workoutLogId, notes = null) {
  return sql`
    UPDATE workout_logs 
    SET completed_at = NOW(), notes = ${notes}
    WHERE id = ${workoutLogId}
  `;
}

export async function getWorkoutHistory(limit = 10) {
  return sql`
    SELECT wl.*, r.name as routine_name,
      (SELECT COUNT(*) FROM workout_sets WHERE workout_log_id = wl.id) as total_sets
    FROM workout_logs wl
    JOIN routines r ON r.id = wl.routine_id
    WHERE wl.completed_at IS NOT NULL
    ORDER BY wl.started_at DESC
    LIMIT ${limit}
  `;
}

export async function getExerciseHistory(exerciseId, limit = 20) {
  return sql`
    SELECT ws.*, wl.started_at
    FROM workout_sets ws
    JOIN workout_logs wl ON wl.id = ws.workout_log_id
    WHERE ws.exercise_id = ${exerciseId}
    ORDER BY wl.started_at DESC, ws.set_number
    LIMIT ${limit}
  `;
}

export async function logWeight(weight, notes = null) {
  return sql`
    INSERT INTO weight_logs (weight, notes)
    VALUES (${weight}, ${notes})
    RETURNING id
  `;
}

export async function getWeightHistory(days = 30) {
  return sql`
    SELECT * FROM weight_logs
    WHERE logged_at >= CURRENT_DATE - INTERVAL '${days} days'
    ORDER BY logged_at DESC
  `;
}
