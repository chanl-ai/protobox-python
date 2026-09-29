import { NextResponse, type NextRequest } from 'next/server'
import { createEmbedSecurityMiddleware } from './middleware/embed-security'

// Allowed origins for embedding (in production, load from database)
const ALLOWED_EMBED_ORIGINS = [
  'http://localhost:3000',
  'http://localhost:3001',
  'http://localhost:3010',
  // Partner domains would be added here dynamically
]

// Create embed security middleware
const embedSecurity = createEmbedSecurityMiddleware({
  allowedOrigins: ALLOWED_EMBED_ORIGINS,
  requireAuth: false,
  maxAge: 86400
})

export async function middleware(request: NextRequest) {
  const response = NextResponse.next()
  
  // Handle embed routes with special headers
  if (request.nextUrl.pathname.startsWith('/integrations') || 
      request.nextUrl.pathname.startsWith('/marketplace')) {
    // Apply embed security middleware
    return embedSecurity(request)
  }
  
  // Get the auth token from cookies
  const authToken = request.cookies.get('auth-token')?.value

  // Public routes that don't require authentication
  const publicRoutes = [
    '/login',
    '/signup', 
    '/forgot-password',
    '/reset-password',
    '/auth',
    '/api',
    '/',
    '/privacy',
    '/terms',
    '/marketplace',  // Legacy embed route
    '/integrations',  // New embed route
    '/embed',  // Allow embed pages without auth
    '/partner-embed-demo.html',  // Demo page
    '/partner-auth-demo.html'  // Partner auth demo
  ]
  
  const isPublicRoute = publicRoutes.some(route => 
    request.nextUrl.pathname === route || request.nextUrl.pathname.startsWith(`${route}/`)
  )

  // Redirect unauthenticated users to login for protected routes
  if (!authToken && !isPublicRoute) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  // Note: We don't redirect authenticated users from auth pages anymore
  // The AuthRedirect component handles intelligent routing based on workspace status

  // Special handling for /dashboard - let the page component handle the redirect
  if (request.nextUrl.pathname === '/dashboard' || request.nextUrl.pathname.startsWith('/dashboard/')) {
    // Allow access to the dashboard redirect page even if authenticated
    return response
  }

  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}