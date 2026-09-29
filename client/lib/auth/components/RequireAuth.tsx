"use client"

import { useAuth } from '../hooks'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'

interface RequireAuthProps {
  children: React.ReactNode
  redirectTo?: string
  loadingComponent?: React.ReactNode
}

export function RequireAuth({ 
  children, 
  redirectTo = '/login',
  loadingComponent 
}: RequireAuthProps) {
  const { user, loading, isAuthenticated } = useAuth()
  const router = useRouter()

  // Auth state evaluation for route protection

  useEffect(() => {
    // Only redirect if we're sure auth is loaded and user is not authenticated
    if (!loading && !isAuthenticated) {
      router.push(redirectTo)
    }
  }, [isAuthenticated, loading, router, redirectTo])

  // Show loading state while auth is initializing
  if (loading) {
    if (loadingComponent) {
      return <>{loadingComponent}</>
    }
    
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-e-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          <h2 className="mt-4 text-lg font-semibold">Loading...</h2>
        </div>
      </div>
    )
  }

  // Only show nothing if we're definitely not authenticated
  if (!isAuthenticated) {
    return null
  }

  return <>{children}</>
}