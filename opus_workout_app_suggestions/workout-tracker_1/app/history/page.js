import { getWorkoutHistory } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function HistoryPage() {
  let workouts = [];
  
  try {
    workouts = await getWorkoutHistory(20);
  } catch (e) {
    console.error('Failed to load history:', e);
  }

  // Group by week
  const groupedByWeek = workouts.reduce((acc, workout) => {
    const date = new Date(workout.started_at);
    const weekStart = new Date(date);
    weekStart.setDate(date.getDate() - date.getDay());
    const weekKey = weekStart.toISOString().split('T')[0];
    
    if (!acc[weekKey]) acc[weekKey] = [];
    acc[weekKey].push(workout);
    return acc;
  }, {});

  return (
    <div className="container">
      <div className="header">
        <h1 className="page-title">Workout History</h1>
      </div>

      {workouts.length === 0 ? (
        <div className="card">
          <p>No workouts logged yet. Start your first workout!</p>
        </div>
      ) : (
        Object.entries(groupedByWeek).map(([weekKey, weekWorkouts]) => (
          <div key={weekKey}>
            <h3 style={{ 
              fontSize: '14px', 
              color: 'var(--text-secondary)', 
              marginBottom: '12px',
              marginTop: '16px'
            }}>
              Week of {new Date(weekKey).toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric' 
              })}
            </h3>
            {weekWorkouts.map((workout) => (
              <div key={workout.id} className="card">
                <div className="history-item">
                  <div>
                    <strong>{workout.routine_name}</strong>
                    <p className="history-date">
                      {new Date(workout.started_at).toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '18px', fontWeight: '600' }}>
                      {workout.total_sets}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      sets
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ))
      )}
    </div>
  );
}
