"use client"

import React, { useState, useEffect } from 'react'
import { useAuth } from '@/lib/auth'
import { useRouter, usePathname } from 'next/navigation'
import { Loader2 } from 'lucide-react'
import { isProtectedRoute, requiresWorkspace, getAuthRedirectPath, getPostAuthRedirectPath } from '@/lib/routes/config'

interface AppLoaderProps {
  children: React.ReactNode
}

/**
 * AppLoader ensures all auth and workspace state is fully resolved
 * before showing any content to prevent UI flickers and redirects
 */
export function AppLoader({ children }: AppLoaderProps) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [hasTimedOut, setHasTimedOut] = useState(false)
  const { isAuthenticated, loading: authLoading, workspaceLoading, workspaces, initialized } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  // Strategy: Only block protected routes with auth loading, everything else is public
  const isProtected = isProtectedRoute(pathname)
  const needsWorkspace = requiresWorkspace(pathname)
  
  console.log(`${isProtected ? '🔒' : '🌐'} AppLoader: ${isProtected ? 'Protected' : 'Public'} route ${pathname}${needsWorkspace ? ' (requires workspace)' : ''}`)

  // Add timeout to prevent infinite loading - reduced timeout for faster fallback
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (!isLoaded) {
        console.warn('AppLoader: Loading timeout reached (3s), showing app anyway')
        setHasTimedOut(true)
        setIsLoaded(true)
      }
    }, 3000) // 3 second timeout - much faster fallback

    return () => clearTimeout(timeout)
  }, [isLoaded])

  useEffect(() => {
    console.log(`🚪 AppLoader: initialized=${initialized}, authLoading=${authLoading}, workspaceLoading=${workspaceLoading}`)
    
    // If we've timed out, don't run the normal flow
    if (hasTimedOut) {
      return
    }

    // Don't stabilize until auth system is initialized
    if (!initialized) {
      console.log('⏳ AppLoader: Waiting for auth initialization')
      return
    }

    // Don't stabilize while critical loading states are active
    // OPTIMIZATION: Only block on authLoading, not workspaceLoading
    // Workspaces can load in background while showing the app
    if (authLoading) {
      console.log('⏳ AppLoader: Waiting for auth loading to complete')
      return
    }

    // All critical state is now resolved - determine final destination
    // OPTIMIZATION: Don't wait for workspaceLoading, it can happen in background
    const isReady = !authLoading && initialized

    if (isReady) {
      console.log('✅ AppLoader: All states ready, determining final destination')
      // Determine where user should go based on auth state
      if (typeof window !== 'undefined') {
        const currentPath = window.location.pathname
        const currentIsProtected = isProtectedRoute(currentPath)
        const currentNeedsWorkspace = requiresWorkspace(currentPath)

        if (!isAuthenticated) {
          // User not authenticated
          if (currentIsProtected) {
            // Trying to access protected route - redirect to login
            console.log('🚫 AppLoader: Unauthenticated user on protected route, redirecting to login')
            router.replace('/login')
            return
          }
          // On public page - stay there
        } else {
          // User is authenticated
          if (currentNeedsWorkspace) {
            // Route needs workspace
            if (workspaceLoading) {
              // Still loading workspaces - wait
              console.log('⏳ AppLoader: Waiting for workspaces to load for protected route')
              return
            } else if (workspaces.length === 0) {
              // No workspaces - redirect to onboarding
              console.log('🎯 AppLoader: No workspaces found, redirecting to onboarding')
              router.replace('/onboarding')
              return
            }
          }
          
          // User is authenticated and on auth pages - redirect to dashboard
          if (currentPath === '/login' || currentPath === '/signup') {
            const redirectPath = getPostAuthRedirectPath(workspaces.length > 0)
            console.log(`🏠 AppLoader: Authenticated user on auth page, redirecting to ${redirectPath}`)
            router.replace(redirectPath)
            return
          }
        }
      }

      // State is stable and user is in the right place
      console.log('🎉 AppLoader: Setting isLoaded = true')
      setIsLoaded(true)
    }
  }, [isAuthenticated, authLoading, workspaceLoading, workspaces.length, initialized, router, hasTimedOut])

  // Show loader while resolving auth state
  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <div className="text-center">
          {/* Show refresh button if timed out, otherwise show loader */}
          {hasTimedOut ? (
            <>
              <div className="mx-auto mb-6 flex h-12 w-12 items-center justify-center">
                <svg
                  className="h-8 w-8 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                Session Loading Issue
              </h3>
              
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 max-w-sm">
                We're having trouble loading your session. This can happen after being idle for a while.
              </p>
              
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Refresh Page
              </button>
            </>
          ) : (
            <>
              {/* Simple rolling icon */}
              <div className="mx-auto mb-6 flex h-12 w-12 items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-blue-600 dark:text-blue-400" />
              </div>
              
              {/* Minimal loading text */}
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Loading...
              </div>
            </>
          )}
        </div>
      </div>
    )
  }

  // For public routes, skip auth loading entirely
  if (!isProtected) {
    return <>{children}</>
  }

  // State is stable - render the app
  return <>{children}</>
}