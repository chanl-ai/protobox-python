// Token storage utilities
export const TOKEN_KEY = 'auth-token'
export const REFRESH_TOKEN_KEY = 'refresh-token'

export interface StorageOptions {
  tokenKey?: string
  refreshTokenKey?: string
  storage?: 'cookie' | 'localStorage' | 'sessionStorage'
  cookieOptions?: {
    maxAge?: number
    sameSite?: 'lax' | 'strict' | 'none'
    secure?: boolean
    path?: string
  }
}

const defaultCookieOptions = {
  maxAge: 604800, // 7 days
  sameSite: 'lax' as const,
  secure: false, // Don't require secure in development
  path: '/'
}

export function storeToken(
  token: string, 
  options: StorageOptions = {}
): void {
  const {
    tokenKey = TOKEN_KEY,
    storage = 'cookie',
    cookieOptions = {}
  } = options


  if (typeof window === 'undefined') return

  switch (storage) {
    case 'cookie':
      const finalOptions = { ...defaultCookieOptions, ...cookieOptions }
      const cookieString = [
        `${tokenKey}=${token}`,
        `path=${finalOptions.path}`,
        `max-age=${finalOptions.maxAge}`,
        `SameSite=${finalOptions.sameSite}`,
        finalOptions.secure && 'Secure'
      ].filter(Boolean).join('; ')
      
      document.cookie = cookieString
      break
      
    case 'localStorage':
      window.localStorage.setItem(tokenKey, token)
      break
      
    case 'sessionStorage':
      window.sessionStorage.setItem(tokenKey, token)
      break
  }
}

export function getToken(
  options: StorageOptions = {}
): string | null {
  const {
    tokenKey = TOKEN_KEY,
    storage = 'cookie'
  } = options

  if (typeof window === 'undefined') return null

  let token: string | null = null

  switch (storage) {
    case 'cookie':
      const cookies = document.cookie.split(';')
      for (const cookie of cookies) {
        const [key, value] = cookie.trim().split('=')
        if (key === tokenKey) {
          token = value
          break
        }
      }
      break
      
    case 'localStorage':
      token = window.localStorage.getItem(tokenKey)
      break
      
    case 'sessionStorage':
      token = window.sessionStorage.getItem(tokenKey)
      break
  }

  return token
}

export function removeToken(
  options: StorageOptions = {}
): void {
  const {
    tokenKey = TOKEN_KEY,
    storage = 'cookie',
    cookieOptions = {}
  } = options

  if (typeof window === 'undefined') return

  switch (storage) {
    case 'cookie':
      const { path = '/' } = cookieOptions
      document.cookie = `${tokenKey}=; path=${path}; expires=Thu, 01 Jan 1970 00:00:01 GMT;`
      break
      
    case 'localStorage':
      window.localStorage.removeItem(tokenKey)
      break
      
    case 'sessionStorage':
      window.sessionStorage.removeItem(tokenKey)
      break
  }
}

export function storeRefreshToken(
  refreshToken: string,
  options: StorageOptions = {}
): void {
  const modifiedOptions = {
    ...options,
    tokenKey: options.refreshTokenKey || REFRESH_TOKEN_KEY
  }
  storeToken(refreshToken, modifiedOptions)
}

export function getRefreshToken(
  options: StorageOptions = {}
): string | null {
  const modifiedOptions = {
    ...options,
    tokenKey: options.refreshTokenKey || REFRESH_TOKEN_KEY
  }
  return getToken(modifiedOptions)
}

export function removeRefreshToken(
  options: StorageOptions = {}
): void {
  const modifiedOptions = {
    ...options,
    tokenKey: options.refreshTokenKey || REFRESH_TOKEN_KEY
  }
  removeToken(modifiedOptions)
}

export function clearAllTokens(
  options: StorageOptions = {}
): void {
  removeToken(options)
  removeRefreshToken(options)
}