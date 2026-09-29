"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "../context/AuthContext"
import { RedirectConfig, BackendIntegration } from "../types"

interface AuthRedirectProps {
  children: React.ReactNode
  redirectConfig?: RedirectConfig
  backendIntegration?: BackendIntegration
}

export function AuthRedirect({ 
  children, 
  redirectConfig,
  backendIntegration 
}: AuthRedirectProps) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    const handleRedirect = async () => {
      // Don't do anything while auth is loading
      if (loading) return
      
      // If no redirect config, just render children
      if (!redirectConfig) return
      
      // Handle sign-out redirect
      if (!user && redirectConfig.afterSignOut) {
        const currentPath = window.location.pathname
        // Only redirect if we're not already on a public page
        if (!['/login', '/signup', '/forgot-password'].includes(currentPath)) {
          router.push(redirectConfig.afterSignOut)
        }
        return
      }
      
      // Don't redirect if we don't have user and token
      if (!user || !user.customToken) return

      try {
        // Auto redirect to workspace if enabled
        if (redirectConfig.autoRedirectToWorkspace && backendIntegration?.fetchWorkspaces) {
          const response = await backendIntegration.fetchWorkspaces()
          
          if (response?.workspaces && response.workspaces.length > 0) {
            // User has workspaces - redirect to their last workspace or first one
            const workspaceId = response.user?.last_workspace_id || response.workspaces[0]._id
            const redirectUrl = redirectConfig.afterSignIn || `/workspace/${workspaceId}/dashboard`
            
            // Replace placeholder with actual workspace ID
            if (redirectUrl.includes('[workspaceId]')) {
              router.push(redirectUrl.replace('[workspaceId]', workspaceId))
            } else {
              router.push(redirectUrl)
            }
          } else if (redirectConfig.requireWorkspace) {
            // New user with no workspaces - redirect to onboarding
            router.push(redirectConfig.requireWorkspace)
          }
        } else if (redirectConfig.afterSignIn) {
          // Simple redirect after sign in
          router.push(redirectConfig.afterSignIn)
        }
      } catch (error) {
        // If redirect fails and we have a fallback, use it
        if (redirectConfig.requireWorkspace) {
          router.push(redirectConfig.requireWorkspace)
        }
      }
    }

    handleRedirect()
  }, [user, loading, router, redirectConfig, backendIntegration])

  return <>{children}</>
}