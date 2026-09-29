"use client"

import React, { useEffect } from 'react'
import { FirebaseAuthConfig, BackendIntegration, AuthUser } from '../types'
import { useAuthStore } from '../stores/auth.store'

interface AuthProviderProps {
  children: React.ReactNode
  config: FirebaseAuthConfig
  backendIntegration?: BackendIntegration
  onAuthStateChange?: (user: AuthUser | null) => void
}

/**
 * AuthProvider now uses Zustand instead of React Context
 * This solves the npm package boundary issue!
 */
export function AuthProvider({ 
  children, 
  config,
  backendIntegration,
  onAuthStateChange
}: AuthProviderProps) {
  const initialize = useAuthStore((state) => state.initialize)
  const initialized = useAuthStore((state) => state.initialized)
  
  useEffect(() => {
    if (!initialized) {
      const unsubscribe = initialize(config, backendIntegration)
      
      // Set up auth state change listener if provided
      if (onAuthStateChange) {
        // Subscribe to all state changes and call onAuthStateChange when user or loading changes
        let previousUser = useAuthStore.getState().user
        
        // Call immediately with current user state
        onAuthStateChange(previousUser)
        
        const unsubscribeStore = useAuthStore.subscribe((state) => {
          // Only call onAuthStateChange if user actually changed
          if (state.user !== previousUser) {
            previousUser = state.user
            onAuthStateChange(state.user)
          }
        })
        
        return () => {
          if (unsubscribe) unsubscribe()
          unsubscribeStore()
        }
      }
      
      return () => {
        if (unsubscribe) unsubscribe()
      }
    }
  }, [config, backendIntegration, initialize, initialized, onAuthStateChange])
  
  return <>{children}</>
}