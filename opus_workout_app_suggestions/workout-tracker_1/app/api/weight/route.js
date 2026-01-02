import { logWeight, getWeightHistory } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const history = await getWeightHistory(30);
    return NextResponse.json(history);
  } catch (error) {
    console.error('Failed to get weight history:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const { weight, notes } = await request.json();
    await logWeight(weight, notes);
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to log weight:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
