"use client"

import { useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuthState } from './useAuthState'

interface UseAuthRedirectOptions {
  redirectTo?: string
  redirectIfAuthenticated?: boolean
  redirectIfNotAuthenticated?: boolean
}

export function useAuthRedirect(options: UseAuthRedirectOptions = {}) {
  const { 
    redirectTo = '/login',
    redirectIfAuthenticated = false,
    redirectIfNotAuthenticated = false
  } = options
  
  const { isAuthenticated, initialized } = useAuthState()
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!initialized) return

    if (redirectIfNotAuthenticated && !isAuthenticated) {
      router.push(`${redirectTo}?from=${encodeURIComponent(pathname)}`)
    }

    if (redirectIfAuthenticated && isAuthenticated) {
      const params = new URLSearchParams(window.location.search)
      const from = params.get('from')
      router.push(from || redirectTo)
    }
  }, [
    initialized, 
    isAuthenticated, 
    redirectIfAuthenticated, 
    redirectIfNotAuthenticated, 
    redirectTo, 
    router, 
    pathname
  ])

  return { isAuthenticated, initialized }
}