"use client"

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthState } from '../../hooks/useAuthState'

interface AuthRedirectProps {
  children: React.ReactNode
  redirectTo?: string
  redirectIfAuthenticated?: boolean
  redirectIfNotAuthenticated?: boolean
  onAuthStateResolved?: (isAuthenticated: boolean) => Promise<string | void>
}

export function AuthRedirect({ 
  children,
  redirectTo = '/dashboard',
  redirectIfAuthenticated = false,
  redirectIfNotAuthenticated = false,
  onAuthStateResolved
}: AuthRedirectProps) {
  const { isAuthenticated, initialized } = useAuthState()
  const router = useRouter()

  useEffect(() => {
    const handleRedirect = async () => {
      if (!initialized) return

      // Custom redirect logic if provided
      if (onAuthStateResolved) {
        const customRedirect = await onAuthStateResolved(isAuthenticated)
        if (customRedirect) {
          router.push(customRedirect)
          return
        }
      }

      // Default redirect logic
      if (redirectIfNotAuthenticated && !isAuthenticated) {
        router.push('/login')
      } else if (redirectIfAuthenticated && isAuthenticated) {
        router.push(redirectTo)
      }
    }

    handleRedirect()
  }, [
    initialized, 
    isAuthenticated, 
    redirectIfAuthenticated, 
    redirectIfNotAuthenticated, 
    redirectTo, 
    router,
    onAuthStateResolved
  ])

  return <>{children}</>
}