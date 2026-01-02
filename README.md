# Workout Tracker

A simple workout tracking app built with Next.js and Neon Postgres. Designed to replace Caliber with a personal, customizable solution.

## Features

- **4-day Upper/Lower Split** - Your exact Caliber routines pre-loaded
- **800+ Exercise Database** - Powered by free-exercise-db with images & instructions
- **Exercise Search & Filter** - Find exercises by muscle, equipment, difficulty
- **Workout Logging** - Track sets, reps, and weight for each exercise
- **Workout History** - View past workouts grouped by week
- **Weight Tracking** - Manual weight logging (FatSecret sync coming soon)
- **Mobile-first UI** - Dark theme matching Caliber's design
- **PWA Ready** - Add to home screen for app-like experience

## Quick Start

### 1. Set up Neon Database

1. Go to [neon.tech](https://neon.tech) and create a free account
2. Create a new project
3. Copy the connection string

### 2. Clone and Configure

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Edit .env.local and add your Neon connection string
```

### 3. Set up Database

Run these SQL files in your Neon console (SQL Editor):

1. First run `lib/schema.sql` - creates all tables
2. Then run `lib/seed.sql` - adds your routines and exercises
3. Import 800+ exercises: `npm run import-exercises`

### 4. Run Locally

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 5. Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Add environment variable in Vercel dashboard:
# DATABASE_URL = your_neon_connection_string
```

## Project Structure

```
workout-app/
├── app/
│   ├── page.js              # Home - quick start workout
│   ├── exercises/           # Exercise browser with search
│   ├── routines/            # View/edit routines
│   ├── log/[id]/            # Log a workout
│   ├── history/             # Workout history
│   ├── weight/              # Weight tracking
│   └── api/                 # API routes
├── lib/
│   ├── db.js                # Database queries
│   ├── schema.sql           # Database schema
│   └── seed.sql             # Your routines data
├── scripts/
│   └── import-exercises.js  # Import free-exercise-db
└── .env.example             # Environment template
```

## Your Routines

Pre-loaded from your Caliber screenshots:

| Day | Routine | Focus |
|-----|---------|-------|
| 1 | Upper A (Push) | Chest, shoulders, triceps |
| 2 | Lower A (Quad) | Squats, lunges, hip thrust |
| 3 | Upper B (Pull) | Back, biceps, traps |
| 4 | Lower B (Hinge) | Deadlifts, hamstrings, core |

## Future Enhancements

- [ ] FatSecret API integration for nutrition/weight sync
- [ ] Exercise history & PR tracking
- [ ] Progress photos
- [ ] Rest timer
- [ ] Muscle diagram visualization
- [ ] Export data to CSV
- [ ] Edit routines in-app

## Tech Stack

- **Frontend**: Next.js 15 (App Router)
- **Database**: Neon Postgres (serverless)
- **Styling**: Plain CSS (no frameworks)
- **Deployment**: Vercel

## Adding Custom Exercises

```sql
INSERT INTO exercises (name, category, equipment, primary_muscles, is_custom)
VALUES ('Your Exercise', 'strength', 'dumbbell', ARRAY['chest'], true);
```

Then link to a routine:

```sql
INSERT INTO routine_exercises (routine_id, exercise_id, exercise_order, target_sets, target_reps)
VALUES (1, (SELECT id FROM exercises WHERE name = 'Your Exercise'), 7, 3, '8-10');
```
