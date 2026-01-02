import { logSet } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function POST(request) {
  try {
    const { workoutLogId, exerciseId, setNumber, weight, reps, rpe } = await request.json();
    
    await logSet(workoutLogId, exerciseId, setNumber, weight, reps, rpe);
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to log set:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
