import { completeWorkout } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function POST(request) {
  try {
    const { workoutLogId, notes } = await request.json();
    
    await completeWorkout(workoutLogId, notes);
    
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to complete workout:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
