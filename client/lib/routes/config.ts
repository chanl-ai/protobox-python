/**
 * Route configuration for authentication and access control
 */

export interface RouteConfig {
  requiresAuth: boolean
  requiresWorkspace?: boolean
  redirectTo?: string
}

/**
 * Routes that require authentication
 * Everything else is considered public by default
 */
export const PROTECTED_ROUTES: Record<string, RouteConfig> = {
  '/dashboard': {
    requiresAuth: true,
    requiresWorkspace: true,
  },
  '/workspace': {
    requiresAuth: true,
    requiresWorkspace: true,
  },
  '/admin': {
    requiresAuth: true,
    requiresWorkspace: true,
  },
  '/settings': {
    requiresAuth: true,
    requiresWorkspace: false,
  },
  '/profile': {
    requiresAuth: true,
    requiresWorkspace: false,
  },
  '/onboarding': {
    requiresAuth: true,
    requiresWorkspace: false,
  },
}

/**
 * Check if a route requires authentication
 */
export function isProtectedRoute(pathname: string): boolean {
  // Check exact match first
  if (PROTECTED_ROUTES[pathname]) {
    return PROTECTED_ROUTES[pathname].requiresAuth
  }
  
  // Check prefix matches for nested routes
  for (const route in PROTECTED_ROUTES) {
    if (pathname.startsWith(route + '/')) {
      return PROTECTED_ROUTES[route].requiresAuth
    }
  }
  
  // Default: public route (no auth required)
  return false
}

/**
 * Check if a route requires a workspace
 */
export function requiresWorkspace(pathname: string): boolean {
  // Check exact match first
  if (PROTECTED_ROUTES[pathname]) {
    return PROTECTED_ROUTES[pathname].requiresWorkspace ?? false
  }
  
  // Check prefix matches for nested routes
  for (const route in PROTECTED_ROUTES) {
    if (pathname.startsWith(route + '/')) {
      return PROTECTED_ROUTES[route].requiresWorkspace ?? false
    }
  }
  
  return false
}

/**
 * Get redirect path for unauthenticated users
 */
export function getAuthRedirectPath(currentPath: string): string {
  // If trying to access a protected route, redirect to login
  if (isProtectedRoute(currentPath)) {
    return '/login'
  }
  
  // Otherwise stay on current page
  return currentPath
}

/**
 * Get redirect path after successful authentication
 */
export function getPostAuthRedirectPath(hasWorkspace: boolean): string {
  if (!hasWorkspace) {
    return '/onboarding'
  }
  return '/dashboard'
}