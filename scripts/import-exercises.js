const { neon } = require('@neondatabase/serverless');

// Free Exercise DB GitHub raw URL
const EXERCISE_DATA_URL = 'https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json';

async function importExercises() {
  const sql = neon(process.env.DATABASE_URL);

  console.log('🔄 Fetching exercise data from free-exercise-db...');

  try {
    // Fetch exercise data
    const response = await fetch(EXERCISE_DATA_URL);
    const exercises = await response.json();

    console.log(`📊 Found ${exercises.length} exercises to import`);

    // Process exercises in batches to avoid memory issues
    const batchSize = 50;
    let imported = 0;
    let skipped = 0;

    for (let i = 0; i < exercises.length; i += batchSize) {
      const batch = exercises.slice(i, i + batchSize);

      for (const exercise of batch) {
        try {
          // Map free-exercise-db format to our schema
          await sql`
            INSERT INTO exercises (
              name, category, equipment, primary_muscles, secondary_muscles,
              instructions, force, level, mechanic, images, source
            ) VALUES (
              ${exercise.name},
              ${exercise.category},
              ${exercise.equipment || null},
              ${exercise.primaryMuscles || []},
              ${exercise.secondaryMuscles || []},
              ${Array.isArray(exercise.instructions) ? exercise.instructions.join('\n\n') : exercise.instructions},
              ${exercise.force || null},
              ${exercise.level || null},
              ${exercise.mechanic || null},
              ${exercise.images ? exercise.images.map(img => `https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/${img}`) : []},
              'free-exercise-db'
            )
            ON CONFLICT (name) DO NOTHING
          `;
          imported++;
        } catch (err) {
          // Exercise already exists or other error
          skipped++;
        }
      }

      // Progress indicator
      process.stdout.write(`\r⏳ Processing: ${Math.min(i + batchSize, exercises.length)}/${exercises.length}`);
    }

    console.log(`\n✅ Import complete!`);
    console.log(`   📥 Imported: ${imported} exercises`);
    console.log(`   ⏭️  Skipped: ${skipped} exercises (already exist)`);

    // Get final count
    const result = await sql`SELECT COUNT(*) as total FROM exercises`;
    console.log(`   🗃️  Total exercises in database: ${result[0].total}`);

  } catch (error) {
    console.error('❌ Import failed:', error);
    process.exit(1);
  }
}

// Check if DATABASE_URL is set
if (!process.env.DATABASE_URL) {
  console.error('❌ DATABASE_URL environment variable is required');
  console.log('💡 Add it to your .env.local file or run:');
  console.log('   export DATABASE_URL="your_neon_connection_string"');
  process.exit(1);
}

importExercises();