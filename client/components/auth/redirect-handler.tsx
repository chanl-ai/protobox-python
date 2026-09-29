"use client"

import { useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/lib/auth/stores/auth.store"
import { logger } from "@/lib/logger"

interface RedirectHandlerProps {
  children: React.ReactNode
  redirectTo?: string // Optional custom redirect path
}

export function RedirectHandler({ 
  children, 
  redirectTo 
}: RedirectHandlerProps) {
  const router = useRouter()
  const hasRedirected = useRef(false)
  
  // Get state from unified store
  const isAuthenticated = useAuthStore(state => state.isAuthenticated)
  const workspaces = useAuthStore(state => state.workspaces)
  const currentWorkspace = useAuthStore(state => state.currentWorkspace)
  const authLoading = useAuthStore(state => state.authLoading)
  const tokenLoading = useAuthStore(state => state.tokenLoading)
  const workspaceLoading = useAuthStore(state => state.workspaceLoading)
  
  // Combined loading state
  const isLoading = authLoading || tokenLoading || workspaceLoading
  
  useEffect(() => {
    // Debug log all states
    console.log('[RedirectHandler] State check:', {
      isLoading,
      authLoading,
      tokenLoading,
      workspaceLoading,
      isAuthenticated,
      hasRedirected: hasRedirected.current,
      workspaceCount: workspaces.length
    })
    
    // Don't redirect while loading
    if (isLoading) {
      logger.log('[RedirectHandler] Still loading, skipping redirect')
      return
    }
    
    // Don't redirect if already done
    if (hasRedirected.current) {
      logger.log('[RedirectHandler] Already redirected, skipping')
      return
    }
    
    // Only redirect if authenticated
    if (!isAuthenticated) {
      logger.log('[RedirectHandler] Not authenticated, no redirect needed')
      return
    }
    
    console.log('[RedirectHandler] Ready to redirect:', {
      isAuthenticated,
      workspaceCount: workspaces.length,
      currentWorkspace: currentWorkspace?.name,
      customRedirect: redirectTo
    })
    
    // Use custom redirect if provided
    if (redirectTo) {
      logger.log('[RedirectHandler] Using custom redirect:', redirectTo)
      hasRedirected.current = true
      router.replace(redirectTo)
      return
    }
    
    // Determine redirect based on workspace state
    if (workspaces.length === 0) {
      logger.log('[RedirectHandler] No workspaces, redirecting to onboarding')
      hasRedirected.current = true
      router.replace('/onboarding')
    } else if (currentWorkspace) {
      // Check if workspace needs onboarding
      if (currentWorkspace.settings?.needs_onboarding) {
        logger.log('[RedirectHandler] Workspace needs onboarding')
        hasRedirected.current = true
        router.replace('/onboarding')
      } else {
        logger.log('[RedirectHandler] Redirecting to dashboard')
        hasRedirected.current = true
        router.replace('/dashboard')
      }
    } else {
      // Has workspaces but no current workspace selected (shouldn't happen)
      logger.warn('[UnifiedRedirectHandler] Has workspaces but no current workspace')
      hasRedirected.current = true
      router.replace('/dashboard')
    }
  }, [
    isAuthenticated, 
    workspaces, 
    currentWorkspace, 
    isLoading, 
    redirectTo, 
    router
  ])
  
  return <>{children}</>
}