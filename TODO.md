# Workout App - Improvement TODO List

Based on code review conducted January 2026.

---

## 🔴 Critical (Security)

### 1. Add Input Validation to API Routes
- [ ] `app/api/exercises/search/route.js` - Add upper bound on `limit` parameter (max 100)
- [ ] `app/api/weight/route.js` - Validate weight is positive and reasonable (0-1000 lbs)
- [ ] `app/api/workouts/log-set/route.js` - Validate weight/reps are positive numbers
- [ ] Don't expose raw `error.message` to clients (could leak DB details)

### 2. Fix XSS Risk in Layout
- [ ] Move inline service worker script from `app/layout.js` (lines 44-56) to external `public/sw-register.js`
- [ ] Remove `dangerouslySetInnerHTML` usage

---

## 🟠 High Priority

### 3. Add Authentication
- [ ] Implement NextAuth.js or similar
- [ ] Protect all API routes with auth middleware
- [ ] Add user_id to workout_logs, weight_logs tables

### 4. Add Rate Limiting
- [ ] Install `@upstash/ratelimit` or similar
- [ ] Apply to all API endpoints

### 5. Fix Race Conditions
- [ ] `app/log/[id]/LogWorkoutClient.js` - Prevent double-click creating duplicate sets
- [ ] Add `disabled` state to buttons during API calls

---

## 🟡 Medium Priority

### 7. Improve Error Handling
- [ ] `app/exercises/page.js` (line 43-44) - Show user-facing error message, not just console.error
- [ ] `app/log/[id]/LogWorkoutClient.js` (line 66-78) - Check API response in `finishWorkout`
- [ ] Add React Error Boundaries for graceful failure

### 8. Performance Improvements
- [ ] Add debounce to exercise search (300ms delay)
  ```javascript
  import { useDebouncedCallback } from 'use-debounce';
  ```
- [ ] Replace `<img>` with Next.js `<Image>` in `app/exercises/page.js`
- [ ] Add pagination to weight history (currently fetches all, slices in UI)
- [ ] Consider full-text search instead of `ILIKE '%query%'` for exercises

### 9. Fix React Anti-patterns
- [ ] `app/log/[id]/LogWorkoutClient.js` (line 134) - Use stable keys instead of array index
  ```javascript
  // Change: key={i}
  // To: key={`set-${exercise.id}-${i}`}
  ```

### 10. Standardize API Responses
- [ ] Use consistent format across all routes: `{ data, error, success }`

---

## 🟢 Low Priority (Enhancements)

### 11. Add Missing Features
- [ ] RPE input in workout logging UI (schema supports it, UI doesn't)
- [ ] Edit/delete logged workouts
- [ ] Edit/delete weight entries
- [ ] Make routine tabs functional (`app/routines/[id]/page.js` lines 27-31)
- [ ] Integrate FatSecret sync button (currently shows "Coming soon")
- [ ] Data export (CSV/JSON)

### 12. Developer Experience
- [ ] Convert to TypeScript
- [ ] Add ESLint + Prettier config
- [ ] Add Jest + React Testing Library tests
- [ ] Add API documentation (OpenAPI/Swagger)
- [ ] Use proper migration tool (Prisma or Drizzle) instead of raw SQL
- [ ] Create `.env.example` with all required variables

### 13. Python Script Improvements
- [ ] Replace `print()` with `logging` module in `fitbit_integration.py`
- [ ] Replace broad `except Exception` with specific exception types
- [ ] Add docstrings to functions

### 14. Database Optimizations
- [ ] Add indexes to main schema if missing:
  - `workout_logs.routine_id`
  - `workout_logs.completed_at`
  - `workout_sets.exercise_id`

---

## 📋 Quick Wins (5-10 min each)

```javascript
// 1. Cap exercise search limit (app/api/exercises/search/route.js)
const limit = Math.min(parseInt(searchParams.get('limit')) || 50, 100);

// 2. Validate weight input (app/api/weight/route.js)
if (!weight || weight <= 0 || weight > 1000) {
  return NextResponse.json({ error: 'Invalid weight' }, { status: 400 });
}

// 3. Disable button during save (LogWorkoutClient.js)
<button disabled={saving} onClick={...}>
  {saving ? 'Saving...' : 'Complete Set'}
</button>

// 4. Add debounce to search
import { useDebouncedCallback } from 'use-debounce';
const debouncedSearch = useDebouncedCallback((value) => setQuery(value), 300);
```

---

## Summary

| Priority | Count | Effort |
|----------|-------|--------|
| 🔴 Critical | 2 | Hours |
| 🟠 High | 3 | Days |
| 🟡 Medium | 4 | Days |
| 🟢 Low | 4 | Weeks |
| Quick Wins | 4 | Minutes |

**Recommended order:** Critical → Quick Wins → High → Medium → Low
