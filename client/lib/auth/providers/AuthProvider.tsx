'use client'

import React, { useEffect, useRef } from 'react'
import { useAuthStore } from '../stores/auth.store'
import { FirebaseConfig } from '../types'
import { useRouter } from 'next/navigation'

interface AuthProviderProps {
  children: React.ReactNode
  firebaseConfig: FirebaseConfig
  onAuthStateChange?: (isAuthenticated: boolean) => void
}

export function AuthProvider({ 
  children, 
  firebaseConfig,
  onAuthStateChange
}: AuthProviderProps) {
  const router = useRouter()
  const initialize = useAuthStore(state => state.initialize)
  const isAuthenticated = useAuthStore(state => state.isAuthenticated)
  const workspaces = useAuthStore(state => state.workspaces)
  const authLoading = useAuthStore(state => state.authLoading)
  const workspaceLoading = useAuthStore(state => state.workspaceLoading)
  const previousAuthState = useRef<boolean | null>(null)
  
  // Initialize Firebase on mount
  useEffect(() => {
    try {
      initialize(firebaseConfig)
    } catch (error) {
      console.error('[AuthProvider] Firebase initialization failed:', error)
    }
  }, [initialize, firebaseConfig])
  
  // Handle auth state changes and routing
  useEffect(() => {
    // Skip if still loading
    if (authLoading || workspaceLoading) {
      return
    }
    
    // Auth state check for routing logic
    
    // Handle authenticated user on auth pages - redirect to dashboard
    if (isAuthenticated && typeof window !== 'undefined') {
      const pathname = window.location.pathname
      
      // If user is authenticated and on auth pages, redirect to dashboard
      if (pathname === '/login' || pathname === '/signup' || pathname === '/') {
        if (workspaces.length === 0) {
          try {
            router.replace('/onboarding')
          } catch (error) {
            console.error('[AuthProvider] router.replace failed, using window.location', error)
            window.location.href = '/onboarding'
          }
        } else {
          try {
            router.replace('/dashboard')
            
            // Add timeout fallback in case router.replace doesn't work
            setTimeout(() => {
              if (window.location.pathname === '/login') {
                window.location.href = '/dashboard'
              }
            }, 1000)
          } catch (error) {
            console.error('[AuthProvider] router.replace failed, using window.location', error)
            window.location.href = '/dashboard'
          }
        }
        
        previousAuthState.current = isAuthenticated
        return
      }
    }
    
    // Check if auth state actually changed
    if (previousAuthState.current === isAuthenticated) {
      return
    }
    
    // Handle logout
    if (previousAuthState.current === true && !isAuthenticated) {
      router.push('/login')
    }
    
    // Handle fresh login (from logged out state)
    if (previousAuthState.current === false && isAuthenticated) {
      // Check if we need to redirect based on workspaces
      if (workspaces.length === 0) {
        router.push('/onboarding')
      } else {
        router.push('/dashboard')
      }
    }
    
    // Update previous state
    previousAuthState.current = isAuthenticated
    
    // Call external handler if provided
    if (onAuthStateChange) {
      onAuthStateChange(isAuthenticated)
    }
  }, [isAuthenticated, workspaces, authLoading, workspaceLoading, router, onAuthStateChange])
  
  return <>{children}</>
}