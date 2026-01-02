import Link from 'next/link';
import { getRoutines, getWorkoutHistory } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function Home() {
  let routines = [];
  let recentWorkouts = [];
  let dbError = null;

  try {
    routines = await getRoutines();
    recentWorkouts = await getWorkoutHistory(5);
  } catch (e) {
    dbError = e.message;
  }

  return (
    <div className="container">
      <div className="header">
        <h1 className="page-title">Workout Tracker</h1>
      </div>

      {dbError && (
        <div className="card" style={{ background: '#7f1d1d' }}>
          <p>Database not connected. Add DATABASE_URL to .env.local</p>
          <p style={{ fontSize: '12px', marginTop: '8px' }}>{dbError}</p>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h2 style={{ fontSize: '16px', margin: 0 }}>Start Workout</h2>
        <Link
          href="/exercises"
          style={{
            fontSize: '12px',
            color: '#007AFF',
            textDecoration: 'none',
            padding: '6px 12px',
            border: '1px solid #007AFF',
            borderRadius: '4px'
          }}
        >
          Browse Exercises
        </Link>
      </div>
      
      {routines.length === 0 && !dbError ? (
        <div className="card">
          <p>No routines yet. Run the seed SQL to add your routines.</p>
        </div>
      ) : (
        routines.map((routine) => (
          <Link 
            key={routine.id} 
            href={`/log/${routine.id}`}
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <div className="card routine-card">
              <h3>{routine.name}</h3>
              <p>{routine.exercise_count} exercises</p>
            </div>
          </Link>
        ))
      )}

      {recentWorkouts.length > 0 && (
        <>
          <h2 style={{ marginBottom: '12px', marginTop: '24px', fontSize: '16px' }}>
            Recent Workouts
          </h2>
          {recentWorkouts.map((workout) => (
            <div key={workout.id} className="card">
              <div className="history-item">
                <div>
                  <strong>{workout.routine_name}</strong>
                  <p className="history-date">
                    {new Date(workout.started_at).toLocaleDateString()}
                  </p>
                </div>
                <span>{workout.total_sets} sets</span>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
