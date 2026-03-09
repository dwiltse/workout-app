# How to Add Task Run Logging to a SKILL.md

Add a **final step** to each scheduled task SKILL.md that calls `log_task_run.py`.
The step should run after all sync steps complete, and handle both success and failure.

---

## Example: fitbit-daily-sync final step

Add this as the last step in your SKILL.md:

```markdown
## Step 4: Log Task Result

Log the outcome of this run to the `task_run_logs` table in Neon.

If all previous steps succeeded, run:
```bash
cd /c/Dev/workout-app && python lib/log_task_run.py \
  --task fitbit-daily-sync \
  --status success \
  --summary "Synced X days of Fitbit data" \
  --duration <total seconds elapsed>
```

If any step failed, run:
```bash
cd /c/Dev/workout-app && python lib/log_task_run.py \
  --task fitbit-daily-sync \
  --status failed \
  --error "<brief description of what failed>"
```
```

---

## Example: fatsecret-daily-sync final step

```markdown
## Step 5: Log Task Result

Log the outcome of this run to the `task_run_logs` table in Neon.

If all previous steps succeeded, run:
```bash
cd /c/Dev/workout-app && python lib/log_task_run.py \
  --task fatsecret-daily-sync \
  --status success \
  --summary "Synced nutrition for X days, weight for Y entries"
```

If any step failed, run:
```bash
cd /c/Dev/workout-app && python lib/log_task_run.py \
  --task fatsecret-daily-sync \
  --status failed \
  --error "<brief description of what failed>"
```
```

---

## Querying Logs (from your Next.js app or Neon console)

```sql
-- All runs today
SELECT * FROM task_run_logs
WHERE completed_at >= CURRENT_DATE
ORDER BY completed_at DESC;

-- Last run per task
SELECT DISTINCT ON (task_id) *
FROM task_run_logs
ORDER BY task_id, completed_at DESC;

-- Any failures in the last 7 days
SELECT * FROM task_run_logs
WHERE status = 'failed'
  AND completed_at >= NOW() - INTERVAL '7 days'
ORDER BY completed_at DESC;
```

---

## Next.js usage (from lib/db.js)

```js
import { getLastTaskRun, getRecentTaskRuns } from '@/lib/db';

// Check if fitbit sync ran successfully today
const lastRun = await getLastTaskRun('fitbit-daily-sync');

// Get last 20 runs across all tasks
const allRuns = await getRecentTaskRuns();
```
