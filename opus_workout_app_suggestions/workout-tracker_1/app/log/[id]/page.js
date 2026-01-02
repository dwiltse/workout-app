import { getRoutineWithExercises, logWorkout } from '@/lib/db';
import LogWorkoutClient from './LogWorkoutClient';

export const dynamic = 'force-dynamic';

export default async function LogWorkoutPage({ params }) {
  const { id } = await params;
  const { routine, exercises } = await getRoutineWithExercises(id);

  if (!routine) {
    return (
      <div className="container">
        <p>Routine not found</p>
      </div>
    );
  }

  // Create a new workout log entry
  const workoutLogId = await logWorkout(id);

  return (
    <LogWorkoutClient 
      routine={routine} 
      exercises={exercises} 
      workoutLogId={workoutLogId}
    />
  );
}
