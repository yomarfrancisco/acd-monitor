import { NextResponse } from 'next/server';
import { wakeBackend } from '@/lib/proxy-utils';

export async function GET() {
  try {
    const success = await wakeBackend();
    
    if (success) {
      return NextResponse.json({
        status: 'success',
        message: 'Backend woken up successfully',
        timestamp: new Date().toISOString()
      });
    } else {
      return NextResponse.json({
        status: 'failed',
        message: 'Failed to wake backend',
        timestamp: new Date().toISOString()
      }, { status: 503 });
    }
  } catch (error) {
    console.error('Wake endpoint error:', error);
    return NextResponse.json({
      status: 'error',
      message: 'Internal server error',
      timestamp: new Date().toISOString()
    }, { status: 500 });
  }
}
