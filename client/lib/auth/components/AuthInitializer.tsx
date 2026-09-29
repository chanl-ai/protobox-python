"use client"

import { useEffect } from 'react'
import { useAuthStore } from '../stores/auth.store'
import { FirebaseAuthConfig, BackendIntegration } from '../types'

interface AuthInitializerProps {
  config: FirebaseAuthConfig
  backendIntegration?: BackendIntegration
  children: React.ReactNode
}

/**
 * Component to initialize the auth store with Firebase config
 * This replaces the AuthProvider and works across npm package boundaries!
 */
export function AuthInitializer({ 
  config, 
  backendIntegration,
  children 
}: AuthInitializerProps) {
  const initialize = useAuthStore((state) => state.initialize)
  const initialized = useAuthStore((state) => state.initialized)
  
  useEffect(() => {
    if (!initialized) {
      initialize(config, backendIntegration)
    }
  }, [config, backendIntegration, initialize, initialized])
  
  return <>{children}</>
}