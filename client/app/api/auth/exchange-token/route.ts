import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const authHeader = request.headers.get('authorization');
  
  if (!authHeader?.startsWith('Bearer ')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const firebaseToken = authHeader.substring(7);

  try {
    // Call Python backend to verify Firebase token and get custom JWT
    const response = await fetch(`${process.env.MCP_SERVER_URL}/admin/api/v1/auth/exchange`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ firebase_token: firebaseToken })
    });

    if (!response.ok) {
      throw new Error('Token exchange failed');
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Token exchange failed' }, 
      { status: 500 }
    );
  }
}