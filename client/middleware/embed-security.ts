import { NextRequest, NextResponse } from 'next/server'

export interface EmbedSecurityConfig {
  allowedOrigins: string[]
  requireAuth?: boolean
  maxAge?: number
}

export function createEmbedSecurityMiddleware(config: EmbedSecurityConfig) {
  return async function embedSecurityMiddleware(request: NextRequest) {
    const response = NextResponse.next()
    const origin = request.headers.get('origin') || ''
    const referer = request.headers.get('referer') || ''
    
    // Check if origin or referer is allowed
    let isAllowed = false
    let allowedOrigin = ''
    
    const checkOrigin = (testOrigin: string) => {
      return config.allowedOrigins.some(allowed => {
        if (allowed === '*') {
          return true
        }
        if (allowed.includes('*')) {
          const pattern = allowed
            .replace(/\./g, '\\.')
            .replace(/\*/g, '.*')
          return new RegExp(`^${pattern}$`).test(testOrigin)
        }
        return allowed === testOrigin
      })
    }
    
    if (origin && checkOrigin(origin)) {
      isAllowed = true
      allowedOrigin = origin
    } else if (referer) {
      try {
        const refererUrl = new URL(referer)
        if (checkOrigin(refererUrl.origin)) {
          isAllowed = true
          allowedOrigin = refererUrl.origin
        }
      } catch {}
    }
    
    // Apply CORS headers if allowed
    if (isAllowed && allowedOrigin) {
      response.headers.set('Access-Control-Allow-Origin', allowedOrigin)
      response.headers.set('Access-Control-Allow-Credentials', 'true')
      response.headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
      response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization')
      response.headers.set('Access-Control-Max-Age', String(config.maxAge || 86400))
    }
    
    // Security headers
    const frameAncestors = isAllowed 
      ? `'self' ${config.allowedOrigins.join(' ')}`
      : "'none'"
    
    response.headers.set(
      'Content-Security-Policy',
      [
        `frame-ancestors ${frameAncestors}`,
      ].join('; ')
    )
    
    response.headers.set('X-Frame-Options', isAllowed ? 'SAMEORIGIN' : 'DENY')
    response.headers.set('X-Content-Type-Options', 'nosniff')
    response.headers.set('X-XSS-Protection', '1; mode=block')
    response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
    
    return response
  }
}