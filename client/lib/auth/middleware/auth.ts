import { NextResponse, type NextRequest } from 'next/server'

export interface AuthMiddlewareConfig {
  publicRoutes?: string[]
  redirectTo?: string
  apiRoutes?: string[]
  cookieName?: string
  onUnauthorized?: (request: NextRequest) => NextResponse | void
}

export function authMiddleware(config: AuthMiddlewareConfig = {}) {
  const {
    publicRoutes = ['/login', '/signup', '/forgot-password', '/reset-password'],
    redirectTo = '/login',
    apiRoutes = ['/api'],
    cookieName = 'auth-token',
    onUnauthorized
  } = config

  return async function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl
    
    // Check if the current route is public
    const isPublicRoute = publicRoutes.some(route => 
      pathname.startsWith(route) || pathname === route
    )
    
    // Check if it's an API route
    const isApiRoute = apiRoutes.some(route => pathname.startsWith(route))
    
    // Get the auth token from cookies
    const authToken = request.cookies.get(cookieName)?.value
    
    // If no auth token and not a public route
    if (!authToken && !isPublicRoute) {
      // Handle unauthorized API requests
      if (isApiRoute) {
        return new NextResponse(
          JSON.stringify({ error: 'Unauthorized' }),
          { 
            status: 401,
            headers: { 'Content-Type': 'application/json' }
          }
        )
      }
      
      // Call custom unauthorized handler if provided
      if (onUnauthorized) {
        const customResponse = onUnauthorized(request)
        if (customResponse) return customResponse
      }
      
      // Redirect to login with return URL
      const redirectUrl = new URL(redirectTo, request.url)
      redirectUrl.searchParams.set('from', pathname)
      return NextResponse.redirect(redirectUrl)
    }
    
    // If authenticated and trying to access auth pages, redirect to home
    if (authToken && (pathname === '/login' || pathname === '/signup')) {
      return NextResponse.redirect(new URL('/', request.url))
    }
    
    return NextResponse.next()
  }
}