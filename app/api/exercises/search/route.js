import { sql } from '@/lib/db';

export async function GET(request) {
  const { searchParams } = new URL(request.url);

  const query = searchParams.get('q') || '';
  const equipment = searchParams.get('equipment');
  const category = searchParams.get('category');
  const muscle = searchParams.get('muscle');
  const level = searchParams.get('level');
  const limit = parseInt(searchParams.get('limit')) || 50;

  try {
    // Build dynamic SQL query with filters
    let sqlQuery = `
      SELECT
        id, name, category, equipment, primary_muscles, secondary_muscles,
        force, level, mechanic, images, instructions
      FROM exercises
      WHERE 1=1
    `;

    const params = [];
    let paramCount = 0;

    // Text search in name and instructions
    if (query) {
      paramCount++;
      sqlQuery += ` AND (name ILIKE $${paramCount} OR instructions ILIKE $${paramCount})`;
      params.push(`%${query}%`);
    }

    // Equipment filter
    if (equipment) {
      paramCount++;
      sqlQuery += ` AND equipment ILIKE $${paramCount}`;
      params.push(`%${equipment}%`);
    }

    // Category filter
    if (category) {
      paramCount++;
      sqlQuery += ` AND category = $${paramCount}`;
      params.push(category);
    }

    // Muscle filter (search in primary_muscles array)
    if (muscle) {
      paramCount++;
      sqlQuery += ` AND $${paramCount} = ANY(primary_muscles)`;
      params.push(muscle);
    }

    // Level filter
    if (level) {
      paramCount++;
      sqlQuery += ` AND level = $${paramCount}`;
      params.push(level);
    }

    sqlQuery += ` ORDER BY name LIMIT $${paramCount + 1}`;
    params.push(limit);

    // Execute query
    const exercises = await sql(sqlQuery, params);

    return Response.json({
      exercises,
      total: exercises.length,
      filters: {
        query,
        equipment,
        category,
        muscle,
        level
      }
    });

  } catch (error) {
    console.error('Exercise search error:', error);
    return Response.json({ error: 'Search failed' }, { status: 500 });
  }
}