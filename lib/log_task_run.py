"""
log_task_run.py — Reusable helper to log scheduled task results to task_run_logs in Neon.

Usage from a SKILL.md step:
    python log_task_run.py --task fitbit-daily-sync --status success --summary "Synced 3 days" --duration 12
    python log_task_run.py --task fitbit-daily-sync --status failed  --error "Token expired"
"""

import argparse
import os
import re
import psycopg2


def get_database_url(env_path=r"C:\Dev\workout-app\.env.local"):
    with open(env_path) as f:
        for line in f:
            m = re.match(r"^DATABASE_URL=['\"]?([^'\"]+)['\"]?", line.strip())
            if m:
                return m.group(1)
    raise ValueError("DATABASE_URL not found in " + env_path)


def log_task_run(task_id, status, summary=None, error_message=None, duration_seconds=None):
    db_url = get_database_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO task_run_logs (task_id, status, summary, error_message, duration_seconds)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (task_id, status, summary, error_message, duration_seconds),
    )
    row_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return row_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Log a scheduled task result to Neon")
    parser.add_argument("--task",     required=True,  help="Task ID, e.g. fitbit-daily-sync")
    parser.add_argument("--status",   required=True,  choices=["success", "failed"])
    parser.add_argument("--summary",  default=None,   help="Short summary of what ran")
    parser.add_argument("--error",    default=None,   help="Error message if status=failed")
    parser.add_argument("--duration", default=None,   type=int, help="Duration in seconds")
    args = parser.parse_args()

    row_id = log_task_run(
        task_id=args.task,
        status=args.status,
        summary=args.summary,
        error_message=args.error,
        duration_seconds=args.duration,
    )
    print(f"Logged task run #{row_id}: {args.task} → {args.status}")
