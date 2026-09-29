/**
 * Shared utilities for API operations
 */

/**
 * Get the backend URL with automatic HTTPS upgrade in production
 * This is the single source of truth for backend URL construction
 */
export function getBackendUrl(): string {
  let url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8090'
  
  // Force HTTPS in production to prevent Mixed Content errors
  // When the app is served over HTTPS, all API calls must also use HTTPS
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    if (url.startsWith('http://') && !url.includes('localhost')) {
      url = url.replace('http://', 'https://')
      console.debug('[API Utils] Upgraded to HTTPS for secure context:', url)
    }
  }
  
  return url
}

/**
 * Get the full API base URL (backend + API prefix)
 */
export function getApiBaseUrl(): string {
  return `${getBackendUrl()}/admin/api/v1`
}

/**
 * Get auth token from cookies (client-side only)
 */
export function getAuthTokenFromCookie(): string | null {
  if (typeof window === 'undefined') return null
  
  const token = document.cookie
    .split('; ')
    .find(row => row.startsWith('auth-token='))
    ?.split('=')[1]
  
  return token || null
}