"use client"

import React, { createContext, useContext, ReactNode } from 'react'

export type AuthProvider = 'firebase' | 'partner'

interface AuthContextValue {
  provider: AuthProvider
  token: string | null
  workspaceId: string | null
  isAuthenticated: boolean
  isEmbedded: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuthContext() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within AuthContextProvider')
  }
  return context
}

interface AuthContextProviderProps {
  children: ReactNode
  provider: AuthProvider
  token: string | null
  workspaceId: string | null
  isEmbedded?: boolean
}

export function AuthContextProvider({
  children,
  provider,
  token,
  workspaceId,
  isEmbedded = false
}: AuthContextProviderProps) {
  const value: AuthContextValue = {
    provider,
    token,
    workspaceId,
    isAuthenticated: !!token,
    isEmbedded
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}