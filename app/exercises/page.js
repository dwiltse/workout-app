'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

export default function ExerciseBrowser() {
  const [exercises, setExercises] = useState([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState({
    equipment: '',
    category: '',
    muscle: '',
    level: ''
  });

  const [availableOptions, setAvailableOptions] = useState({
    equipment: [],
    categories: [],
    muscles: [],
    levels: []
  });

  useEffect(() => {
    searchExercises();
  }, [query, filters]);

  const searchExercises = async () => {
    setLoading(true);

    const params = new URLSearchParams({
      q: query,
      limit: '100',
      ...Object.fromEntries(
        Object.entries(filters).filter(([_, value]) => value)
      )
    });

    try {
      const response = await fetch(`/api/exercises/search?${params}`);
      const data = await response.json();
      setExercises(data.exercises || []);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateFilter = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setQuery('');
    setFilters({
      equipment: '',
      category: '',
      muscle: '',
      level: ''
    });
  };

  return (
    <div className="container">
      <div className="header">
        <Link href="/" style={{ textDecoration: 'none', color: '#666' }}>
          ← Back
        </Link>
        <h1 className="page-title">Exercise Browser</h1>
      </div>

      {/* Search & Filters */}
      <div className="card">
        <input
          type="text"
          placeholder="Search exercises..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{
            width: '100%',
            padding: '12px',
            border: '1px solid #444',
            borderRadius: '6px',
            background: '#222',
            color: 'white',
            marginBottom: '12px'
          }}
        />

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
          <select
            value={filters.equipment}
            onChange={(e) => updateFilter('equipment', e.target.value)}
            style={{
              padding: '8px',
              border: '1px solid #444',
              borderRadius: '4px',
              background: '#222',
              color: 'white'
            }}
          >
            <option value="">All Equipment</option>
            <option value="dumbbell">Dumbbell</option>
            <option value="barbell">Barbell</option>
            <option value="bodyweight">Bodyweight</option>
            <option value="cable">Cable</option>
            <option value="machine">Machine</option>
          </select>

          <select
            value={filters.category}
            onChange={(e) => updateFilter('category', e.target.value)}
            style={{
              padding: '8px',
              border: '1px solid #444',
              borderRadius: '4px',
              background: '#222',
              color: 'white'
            }}
          >
            <option value="">All Categories</option>
            <option value="strength">Strength</option>
            <option value="cardio">Cardio</option>
            <option value="stretching">Stretching</option>
          </select>

          <select
            value={filters.muscle}
            onChange={(e) => updateFilter('muscle', e.target.value)}
            style={{
              padding: '8px',
              border: '1px solid #444',
              borderRadius: '4px',
              background: '#222',
              color: 'white'
            }}
          >
            <option value="">All Muscles</option>
            <option value="chest">Chest</option>
            <option value="back">Back</option>
            <option value="shoulders">Shoulders</option>
            <option value="biceps">Biceps</option>
            <option value="triceps">Triceps</option>
            <option value="quadriceps">Quadriceps</option>
            <option value="hamstrings">Hamstrings</option>
            <option value="glutes">Glutes</option>
            <option value="abdominals">Abs</option>
          </select>

          <select
            value={filters.level}
            onChange={(e) => updateFilter('level', e.target.value)}
            style={{
              padding: '8px',
              border: '1px solid #444',
              borderRadius: '4px',
              background: '#222',
              color: 'white'
            }}
          >
            <option value="">All Levels</option>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="expert">Expert</option>
          </select>
        </div>

        {(query || Object.values(filters).some(f => f)) && (
          <button
            onClick={clearFilters}
            style={{
              marginTop: '8px',
              padding: '6px 12px',
              border: 'none',
              borderRadius: '4px',
              background: '#444',
              color: 'white',
              cursor: 'pointer'
            }}
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Results */}
      <div style={{ marginBottom: '12px', color: '#999', fontSize: '14px' }}>
        {loading ? 'Searching...' : `${exercises.length} exercises found`}
      </div>

      {exercises.map((exercise) => (
        <div key={exercise.id} className="card" style={{ marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            {exercise.images && exercise.images[0] && (
              <img
                src={exercise.images[0]}
                alt={exercise.name}
                style={{
                  width: '60px',
                  height: '60px',
                  objectFit: 'cover',
                  borderRadius: '4px',
                  background: '#333'
                }}
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            )}

            <div style={{ flex: 1 }}>
              <h3 style={{ margin: '0 0 4px 0', fontSize: '16px' }}>{exercise.name}</h3>

              <div style={{
                display: 'flex',
                gap: '12px',
                marginBottom: '8px',
                fontSize: '12px',
                color: '#999'
              }}>
                {exercise.equipment && <span>📦 {exercise.equipment}</span>}
                {exercise.level && <span>📊 {exercise.level}</span>}
                {exercise.force && <span>💪 {exercise.force}</span>}
              </div>

              {exercise.primary_muscles && exercise.primary_muscles.length > 0 && (
                <div style={{ fontSize: '12px', color: '#666' }}>
                  🎯 {exercise.primary_muscles.join(', ')}
                </div>
              )}

              {exercise.instructions && (
                <details style={{ marginTop: '8px' }}>
                  <summary style={{ cursor: 'pointer', fontSize: '12px', color: '#999' }}>
                    View Instructions
                  </summary>
                  <div style={{
                    marginTop: '8px',
                    fontSize: '12px',
                    lineHeight: '1.4',
                    color: '#ccc'
                  }}>
                    {exercise.instructions.split('\n\n').map((step, index) => (
                      <p key={index} style={{ margin: '4px 0' }}>{step}</p>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        </div>
      ))}

      {!loading && exercises.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: '#666' }}>
          <p>No exercises found.</p>
          <p style={{ fontSize: '12px', marginTop: '8px' }}>
            Try adjusting your search terms or filters.
          </p>
        </div>
      )}
    </div>
  );
}