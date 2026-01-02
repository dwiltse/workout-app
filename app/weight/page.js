'use client';

import { useState, useEffect } from 'react';

export default function WeightPage() {
  const [weight, setWeight] = useState('');
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/weight');
      const data = await res.json();

      // Handle API errors or ensure we have an array
      if (data.error) {
        console.error('API error:', data.error);
        setHistory([]);
      } else if (Array.isArray(data)) {
        setHistory(data);
      } else {
        console.warn('Unexpected API response:', data);
        setHistory([]);
      }
    } catch (e) {
      console.error('Failed to fetch weight history:', e);
      setHistory([]);
    }
    setLoading(false);
  };

  const logWeight = async () => {
    if (!weight) return;
    setSaving(true);
    try {
      await fetch('/api/weight', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weight: parseFloat(weight) }),
      });
      setWeight('');
      fetchHistory();
    } catch (e) {
      console.error('Failed to log weight:', e);
    }
    setSaving(false);
  };

  // Calculate stats (with safety checks)
  const latestWeight = history.length > 0 ? history[0]?.weight : null;
  const weekAgo = history.length > 0 ? history.find((w) => {
    const daysDiff = (new Date() - new Date(w.logged_at)) / (1000 * 60 * 60 * 24);
    return daysDiff >= 7;
  }) : null;
  const weekChange = (weekAgo && latestWeight) ? (latestWeight - weekAgo.weight).toFixed(1) : null;

  return (
    <div className="container">
      <div className="header">
        <h1 className="page-title">Weight Tracker</h1>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{latestWeight || '--'}</div>
          <div className="stat-label">Current (lbs)</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ 
            color: weekChange > 0 ? '#ef4444' : weekChange < 0 ? '#22c55e' : 'inherit'
          }}>
            {weekChange ? `${weekChange > 0 ? '+' : ''}${weekChange}` : '--'}
          </div>
          <div className="stat-label">7-day change</div>
        </div>
      </div>

      {/* Log weight */}
      <div className="card">
        <h3 style={{ marginBottom: '12px' }}>Log Today's Weight</h3>
        <div style={{ display: 'flex', gap: '12px' }}>
          <input
            type="number"
            step="0.1"
            placeholder="Weight in lbs"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            style={{ flex: 1 }}
          />
          <button 
            className="btn" 
            onClick={logWeight}
            disabled={saving || !weight}
            style={{ width: 'auto', padding: '12px 24px' }}
          >
            {saving ? '...' : 'Log'}
          </button>
        </div>
      </div>

      {/* FatSecret integration placeholder */}
      <div className="card" style={{ marginTop: '16px', background: 'var(--bg-secondary)' }}>
        <h3 style={{ marginBottom: '8px' }}>📱 FatSecret Sync</h3>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
          Coming soon: Sync weight and nutrition data from FatSecret automatically.
        </p>
      </div>

      {/* History */}
      <h2 style={{ marginTop: '24px', marginBottom: '12px', fontSize: '16px' }}>
        Recent Entries
      </h2>
      
      {loading ? (
        <p>Loading...</p>
      ) : history.length === 0 ? (
        <div className="card">
          <p>No weight entries yet.</p>
        </div>
      ) : (
        history.slice(0, 14).map((entry) => (
          <div key={entry.id} className="card">
            <div className="history-item">
              <span>{new Date(entry.logged_at).toLocaleDateString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
              })}</span>
              <span style={{ fontWeight: '600' }}>{entry.weight} lbs</span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
