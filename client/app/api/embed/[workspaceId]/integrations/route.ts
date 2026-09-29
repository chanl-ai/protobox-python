import { NextRequest, NextResponse } from 'next/server'

/**
 * API proxy for embedded integrations
 * Validates API key and fetches integrations from the server
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { workspaceId: string } }
) {
  try {
    const apiKey = request.headers.get('x-api-key')
    
    // For testing, accept any API key starting with "test-"
    // In production, validate against partner records
    if (!apiKey || !apiKey.startsWith('test-')) {
      return NextResponse.json(
        { error: 'Invalid API key' },
        { status: 401 }
      )
    }

    // Fetch integrations from the server
    const serverUrl = process.env.MCP_SERVER_URL || 'http://localhost:8090'
    const response = await fetch(
      `${serverUrl}/admin/api/v1/workspaces/${params.workspaceId}/integrations`,
      {
        headers: {
          'Content-Type': 'application/json',
          // In production, use proper service-to-service auth
          'X-API-Key': process.env.MCP_ADMIN_API_KEY ?? ''
        }
      }
    )

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch integrations' },
        { status: response.status }
      )
    }

    const integrations = await response.json()
    
    // Add CORS headers for embedding
    const headers = new Headers({
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*', // In production, restrict to partner domains
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-API-Key'
    })

    return NextResponse.json(integrations, { headers })
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// Handle preflight requests
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, X-API-Key'
    }
  })
}