'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function LogWorkoutClient({ routine, exercises, workoutLogId }) {
  const router = useRouter();
  const [sets, setSets] = useState({});
  const [currentExercise, setCurrentExercise] = useState(0);
  const [saving, setSaving] = useState(false);

  // Initialize sets state for each exercise
  useEffect(() => {
    const initialSets = {};
    exercises.forEach((ex) => {
      initialSets[ex.exercise_id] = Array.from({ length: ex.target_sets }, (_, i) => ({
        setNumber: i + 1,
        weight: '',
        reps: '',
        completed: false,
      }));
    });
    setSets(initialSets);
  }, [exercises]);

  const handleSetChange = (exerciseId, setIndex, field, value) => {
    setSets((prev) => ({
      ...prev,
      [exerciseId]: prev[exerciseId].map((s, i) =>
        i === setIndex ? { ...s, [field]: value } : s
      ),
    }));
  };

  const markSetComplete = async (exerciseId, setIndex) => {
    const set = sets[exerciseId][setIndex];
    if (!set.weight || !set.reps) return;

    setSaving(true);
    try {
      await fetch('/api/workouts/log-set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workoutLogId,
          exerciseId,
          setNumber: set.setNumber,
          weight: parseFloat(set.weight),
          reps: parseInt(set.reps),
        }),
      });

      setSets((prev) => ({
        ...prev,
        [exerciseId]: prev[exerciseId].map((s, i) =>
          i === setIndex ? { ...s, completed: true } : s
        ),
      }));
    } catch (e) {
      console.error('Failed to log set:', e);
    }
    setSaving(false);
  };

  const finishWorkout = async () => {
    setSaving(true);
    try {
      await fetch('/api/workouts/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workoutLogId }),
      });
      router.push('/history');
    } catch (e) {
      console.error('Failed to complete workout:', e);
    }
    setSaving(false);
  };

  const ex = exercises[currentExercise];
  const exerciseSets = sets[ex?.exercise_id] || [];
  const allSetsComplete = exerciseSets.every((s) => s.completed);

  return (
    <div className="container">
      <div className="header">
        <Link href="/">
          <button className="back-btn">←</button>
        </Link>
        <h1 className="page-title">{routine.name}</h1>
      </div>

      {/* Exercise navigation */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', overflowX: 'auto' }}>
        {exercises.map((e, i) => (
          <button
            key={e.id}
            onClick={() => setCurrentExercise(i)}
            style={{
              padding: '8px 16px',
              borderRadius: '20px',
              border: 'none',
              background: i === currentExercise ? 'var(--accent)' : 'var(--bg-card)',
              color: 'white',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              fontSize: '13px',
            }}
          >
            {i + 1}
          </button>
        ))}
      </div>

      {/* Current exercise */}
      <div className="card">
        <h2 style={{ marginBottom: '8px' }}>{ex?.name}</h2>
        <div className="muscles" style={{ marginBottom: '16px' }}>
          {ex?.primary_muscles?.join(', ')}
        </div>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          Target: {ex?.target_sets} sets × {ex?.target_reps} reps
        </p>

        {/* Sets */}
        <div style={{ marginBottom: '8px' }}>
          <div className="set-row" style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
            <span>Set</span>
            <span>Weight (lbs)</span>
            <span>Reps</span>
            <span></span>
          </div>
          {exerciseSets.map((set, i) => (
            <div key={i} className="set-row">
              <div className={`set-number ${set.completed ? 'set-complete' : ''}`}>
                {set.setNumber}
              </div>
              <input
                type="number"
                placeholder="0"
                value={set.weight}
                onChange={(e) => handleSetChange(ex.exercise_id, i, 'weight', e.target.value)}
                disabled={set.completed}
              />
              <input
                type="number"
                placeholder="0"
                value={set.reps}
                onChange={(e) => handleSetChange(ex.exercise_id, i, 'reps', e.target.value)}
                disabled={set.completed}
              />
              <button
                onClick={() => markSetComplete(ex.exercise_id, i)}
                disabled={set.completed || saving || !set.weight || !set.reps}
                style={{
                  background: set.completed ? 'var(--success)' : 'var(--bg-secondary)',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '8px',
                  cursor: set.completed ? 'default' : 'pointer',
                  color: 'white',
                }}
              >
                {set.completed ? '✓' : '→'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Navigation buttons */}
      <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
        {currentExercise > 0 && (
          <button
            className="btn btn-secondary"
            onClick={() => setCurrentExercise((c) => c - 1)}
            style={{ flex: 1 }}
          >
            Previous
          </button>
        )}
        {currentExercise < exercises.length - 1 ? (
          <button
            className="btn"
            onClick={() => setCurrentExercise((c) => c + 1)}
            style={{ flex: 1 }}
          >
            Next Exercise
          </button>
        ) : (
          <button
            className="btn"
            onClick={finishWorkout}
            disabled={saving}
            style={{ flex: 1 }}
          >
            {saving ? 'Saving...' : 'Finish Workout'}
          </button>
        )}
      </div>
    </div>
  );
}
