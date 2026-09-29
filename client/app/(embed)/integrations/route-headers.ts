import { NextResponse } from 'next/server'

export function addEmbedHeaders(response: NextResponse, allowedOrigins: string[]) {
  // Allow embedding in iframes from specific origins
  const cspDirectives = [
    "default-src 'self'",
    `frame-ancestors ${allowedOrigins.join(' ')}`,
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'", // For Next.js
    "style-src 'self' 'unsafe-inline'", // For Tailwind
    "img-src 'self' data: https:",
    `connect-src 'self' ${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8090"}`
  ]

  response.headers.set('Content-Security-Policy', cspDirectives.join('; '))
  response.headers.set('X-Frame-Options', 'ALLOWALL') // Override Next.js default
  
  return response
}