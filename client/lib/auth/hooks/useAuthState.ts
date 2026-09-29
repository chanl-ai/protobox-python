"use client"

import { useAuth } from './useAuth'

export function useAuthState() {
  const { user, loading, error, initialized } = useAuth()
  
  return {
    user,
    loading,
    error,
    initialized,
    isAuthenticated: !!user,
    isLoading: loading,
    isError: !!error
  }
}