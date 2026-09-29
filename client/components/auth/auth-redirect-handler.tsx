"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { protoboxClient } from "@/lib/api/protobox-client"

interface AuthRedirectHandlerProps {
  children: React.ReactNode
}

export function AuthRedirectHandler({ children }: AuthRedirectHandlerProps) {
  const { user, loading } = useAuth()
  const router = useRouter()
  
  // Debug: Log every render

  useEffect(() => {
    const handleRedirect = async () => {
      
      // Don't do anything while auth is loading
      if (loading) {
        return
      }
      
      // If user is authenticated, check for token
      if (user) {
        // Wait a bit for token exchange to complete if needed
        if (!user.customToken) {
          // Check localStorage for token
          const storedToken = localStorage.getItem('auth-token');
          if (!storedToken) {
            // Wait and retry once
            setTimeout(() => {
              handleRedirect();
            }, 1000);
            return;
          }
        }
        
        // Now proceed with redirect
        if (user.customToken || localStorage.getItem('auth-token')) {
          try {
            const response = await protoboxClient.getWorkspaces()

            if (response.data) {
              const data = response.data
              
              if (data.workspaces && data.workspaces.length > 0) {
                // User has workspaces - redirect to their last workspace or first one
                const workspaceId = data.user?.last_workspace_id || data.workspaces[0]._id
                router.push('/dashboard')
              } else {
                // New user with no workspaces - redirect to onboarding
                router.push('/onboarding')
              }
            } else {
              // If the API call fails, redirect to onboarding as a fallback
              router.push('/onboarding')
            }
          } catch (error) {
            router.push('/onboarding')
          }
        }
      }
    }

    handleRedirect()
  }, [user, loading, router])

  return <>{children}</>
}