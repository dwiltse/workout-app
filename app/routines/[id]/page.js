import Link from 'next/link';
import { getRoutineWithExercises } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function RoutinePage({ params }) {
  const { id } = await params;
  const { routine, exercises } = await getRoutineWithExercises(id);

  if (!routine) {
    return (
      <div className="container">
        <p>Routine not found</p>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="header">
        <Link href="/routines">
          <button className="back-btn">←</button>
        </Link>
        <h1 className="page-title">{routine.name}</h1>
      </div>

      <div className="tabs">
        <span className="tab active">Exercises</span>
        <span className="tab">Overview</span>
        <span className="tab">Notes</span>
      </div>

      {exercises.map((ex) => (
        <div key={ex.id} className="card exercise-card">
          <div className="exercise-info">
            <div className="exercise-name">{ex.name}</div>
            <span className="exercise-meta">
              {ex.target_sets} sets × {ex.target_reps} reps
            </span>
            <div className="muscles">
              {ex.primary_muscles?.join(', ')}
              {ex.secondary_muscles?.length > 0 && (
                <span style={{ opacity: 0.7 }}>
                  {' '}• {ex.secondary_muscles.join(', ')}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}

      <Link href={`/log/${id}`} style={{ textDecoration: 'none' }}>
        <button className="btn" style={{ marginTop: '16px' }}>
          Start Workout
        </button>
      </Link>
    </div>
  );
}
