import { NextRequest, NextResponse } from 'next/server'
import { validatePartnerAccess } from '@/lib/partner-security'

export async function POST(request: NextRequest) {
  try {
    const { partnerId, origin } = await request.json()

    if (!partnerId || !origin) {
      return NextResponse.json(
        { valid: false, reason: 'Missing required parameters' },
        { status: 400 }
      )
    }

    // Validate partner access
    const validation = await validatePartnerAccess(partnerId, origin)

    return NextResponse.json(validation)
  } catch (error) {
    return NextResponse.json(
      { valid: false, reason: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function OPTIONS(request: NextRequest) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  })
}