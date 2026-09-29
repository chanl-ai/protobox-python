import { NextRequest, NextResponse } from 'next/server'
import { logger } from '@/lib/logger'

interface OAuthRequestBody {
  client_id: string
  redirect_uri: string
  scope: string
  code_challenge?: string
  code_challenge_method?: string
  state?: string
  workspace_id?: string
  action?: 'approve' | 'deny'
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json() as OAuthRequestBody
    const authHeader = request.headers.get('authorization')
    
    logger.log('[OAuth API] Authorization header:', authHeader ? 'Present' : 'Missing')
    logger.log('[OAuth API] Request body:', { 
      client_id: body.client_id,
      action: body.action,
      has_challenge: !!body.code_challenge 
    })
    
    if (!authHeader) {
      logger.error('[OAuth API] No authorization header provided')
      return NextResponse.json(
        { error: 'Authorization required' },
        { status: 401 }
      )
    }

    // Check if user approved or denied
    if (body.action === 'deny') {
      // User denied authorization
      const redirectUrl = new URL(body.redirect_uri)
      redirectUrl.searchParams.set('error', 'access_denied')
      redirectUrl.searchParams.set('error_description', 'User denied authorization')
      if (body.state) {
        redirectUrl.searchParams.set('state', body.state)
      }
      
      return NextResponse.json({
        redirect_uri: redirectUrl.toString(),
        error: 'access_denied'
      })
    }

    // Forward the authorization request to backend using the consent endpoint (only if approved)
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8090'
    
    // Use query parameters for OAuth authorization 
    const authParams = new URLSearchParams()
    authParams.set('client_id', body.client_id)
    authParams.set('redirect_uri', body.redirect_uri)
    authParams.set('scope', body.scope)
    if (body.code_challenge) {
      authParams.set('code_challenge', body.code_challenge)
    }
    authParams.set('code_challenge_method', body.code_challenge_method || 'S256')
    authParams.set('state', body.state || '')
    if (body.workspace_id) {
      authParams.set('workspace_id', body.workspace_id)
    }
    
    const response = await fetch(`${backendUrl}/admin/api/v1/oauth/authorize/consent?${authParams}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authHeader,
      },
    })

    if (!response.ok) {
      const error = await response.json()
      logger.error('[OAuth API] Authorization failed:', error)
      return NextResponse.json(error, { status: response.status })
    }

    const result = await response.json() as Record<string, any>
    
    // If we got an authorization code, build the redirect URI
    if (result.code) {
      const redirectUrl = new URL(body.redirect_uri)
      redirectUrl.searchParams.set('code', result.code)
      if (body.state) {
        redirectUrl.searchParams.set('state', body.state)
      }
      
      return NextResponse.json({
        redirect_uri: redirectUrl.toString(),
        code: result.code
      })
    }

    return NextResponse.json(result)
  } catch (error) {
    logger.error('[OAuth API] Error processing authorization:', error as Record<string, any>)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}