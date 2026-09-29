import { NextRequest, NextResponse } from 'next/server'
import crypto from 'crypto'

// Mock partner database - in production this would be in MongoDB
const MOCK_PARTNERS = {
  'demo_partner': {
    secret_key: 'demo_secret_key_123',
    workspace_mappings: {
      'demo_user_1': '688000d0543c2e11c71283c2',
      'demo_user_2': '688000d0543c2e11c71283c3'
    },
    allowed_endpoints: ['integrations', 'actions'],
    rate_limit: 100
  },
  'test_partner': {
    secret_key: 'test_secret_key_456',
    workspace_mappings: {
      'test_user_1': '688000d0543c2e11c71283c2',  // Using existing workspace for testing
      'test_user_2': '688000d0543c2e11c71283c3',
      'user123': '688000d0543c2e11c71283c2',  // For SDK testing
      'user_123': '688000d0543c2e11c71283c2'  // For React SDK test app
    },
    allowed_endpoints: ['integrations', 'actions', 'settings', 'tenants'],
    rate_limit: 200
  }
}

function validatePartnerRequest(
  payload: any,
  signature: string,
  secretKey: string
): boolean {
  const expectedSignature = crypto
    .createHmac('sha256', secretKey)
    .update(JSON.stringify(payload))
    .digest('hex')
  
  return signature === expectedSignature
}

/**
 * Catch-all partner API endpoint
 * Handles all partner API requests with signed authentication
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  try {
    const { path } = await params
    
    const signature = request.headers.get('x-partner-signature')
    if (!signature) {
      return NextResponse.json(
        { error: 'Missing signature' },
        { status: 401 }
      )
    }

    const payload = await request.json()
    
    const { partner_id, partner_user_id, timestamp } = payload

    // Validate timestamp
    const now = Date.now()
    if (!timestamp || Math.abs(now - timestamp) > 5 * 60 * 1000) {
      return NextResponse.json(
        { error: 'Invalid or expired timestamp' },
        { status: 401 }
      )
    }

    // Get partner config
    const partner = MOCK_PARTNERS[partner_id as keyof typeof MOCK_PARTNERS]
    if (!partner) {
      return NextResponse.json(
        { error: 'Invalid partner' },
        { status: 401 }
      )
    }

    // Validate signature
    
    const isValid = validatePartnerRequest(payload, signature, partner.secret_key)
    
    if (!isValid) {
      // Generate expected signature for debugging
      const expectedSig = crypto
        .createHmac('sha256', partner.secret_key)
        .update(JSON.stringify(payload))
        .digest('hex')
      
      return NextResponse.json(
        { error: 'Invalid signature' },
        { status: 401 }
      )
    }

    // Build the backend endpoint path
    const endpointPath = path.join('/')
    
    // Handle tenant creation separately
    if (endpointPath === 'tenants') {
      // For tenant creation, create/get workspace mapping
      const { tenant_id, tenant_name } = payload.data || {}
      
      // Check if tenant already has a workspace
      let workspaceId = partner.workspace_mappings[tenant_id as keyof typeof partner.workspace_mappings]
      
      if (!workspaceId) {
        // In production, would create a new workspace via backend
        // For now, return error
        return NextResponse.json(
          { error: 'Tenant not found. In production, would create new workspace.' },
          { status: 404 }
        )
      }
      
      return NextResponse.json({
        workspace_id: workspaceId,
        tenant_id: tenant_id,
        status: 'active'
      })
    }
    
    // For other endpoints, require partner_user_id
    const workspaceId = partner.workspace_mappings[partner_user_id as keyof typeof partner.workspace_mappings]
    if (!workspaceId) {
      return NextResponse.json(
        { error: 'User not mapped to workspace' },
        { status: 404 }
      )
    }
    
    // Fetch from backend
    const serverUrl = process.env.MCP_SERVER_URL || 'http://localhost:8090'
    const backendUrl = `${serverUrl}/admin/api/v1/workspaces/${workspaceId}/${endpointPath}`
    
    // Determine the correct HTTP method based on the endpoint
    // Partner always sends POST, but backend expects GET for listing endpoints
    let method = 'POST'
    if (endpointPath === 'integrations' || endpointPath === 'actions') {
      method = 'GET'
    }

    const response = await fetch(backendUrl, {
      method,
      headers: {
        'Content-Type': 'application/json'
        // Admin API doesn't require authentication in development
      },
      body: method !== 'GET' && payload.data ? JSON.stringify(payload.data) : undefined
    })


    if (!response.ok) {
      const errorText = await response.text()
      return NextResponse.json(
        { error: 'Backend request failed', details: errorText },
        { status: response.status }
      )
    }

    const data = await response.json()

    // Return with CORS headers
    return NextResponse.json(data, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Partner-Signature'
      }
    })

  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-Partner-Signature'
    }
  })
}