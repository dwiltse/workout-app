import Link from 'next/link';
import { getRoutines } from '@/lib/db';

export const dynamic = 'force-dynamic';

export default async function RoutinesPage() {
  let routines = [];
  
  try {
    routines = await getRoutines();
  } catch (e) {
    console.error('Failed to load routines:', e);
  }

  return (
    <div className="container">
      <div className="header">
        <h1 className="page-title">My Routines</h1>
      </div>

      {routines.map((routine) => (
        <Link 
          key={routine.id} 
          href={`/routines/${routine.id}`}
          style={{ textDecoration: 'none', color: 'inherit' }}
        >
          <div className="card routine-card">
            <div className="card-header">
              <h3>{routine.name}</h3>
              <span style={{ color: 'var(--text-secondary)' }}>→</span>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              {routine.description}
            </p>
            <p style={{ marginTop: '8px', fontSize: '13px' }}>
              {routine.exercise_count} exercises
            </p>
          </div>
        </Link>
      ))}
    </div>
  );
}
