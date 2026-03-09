-- Task Run Logs Schema
-- Tracks execution status of Claude scheduled tasks (fitbit-daily-sync, fatsecret-daily-sync, etc.)
-- Run this in your Neon console to add the table

CREATE TABLE IF NOT EXISTS task_run_logs (
  id                SERIAL PRIMARY KEY,
  task_id           VARCHAR(100) NOT NULL,   -- 'fitbit-daily-sync', 'fatsecret-daily-sync', 'fitbit-sync'
  status            VARCHAR(20)  NOT NULL,   -- 'success' or 'failed'
  completed_at      TIMESTAMP    DEFAULT NOW(),
  duration_seconds  INTEGER,                 -- optional: how long the task took
  summary           TEXT,                    -- optional: e.g. "Synced 3 days of data"
  error_message     TEXT                     -- optional: populated on failure
);

-- Indexes for common queries (filter by task, date, status)
CREATE INDEX IF NOT EXISTS idx_task_run_logs_task_id      ON task_run_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_task_run_logs_completed_at ON task_run_logs(completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_run_logs_status       ON task_run_logs(status);
