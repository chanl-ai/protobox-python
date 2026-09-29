"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/firebase/auth-context"
import { protoboxClient } from "@/lib/api/protobox-client"

interface AuthRedirectProps {
  children: React.ReactNode
}

export function AuthRedirect({ children }: AuthRedirectProps) {
  const { user, customToken, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    const handleRedirect = async () => {
      if (loading) return

      if (user && customToken) {
        try {
          
          // Fetch workspaces
          const response = await protoboxClient.getWorkspaces()

          if (response.data) {
            const data = response.data
            
            if (data.workspaces && data.workspaces.length > 0) {
              // User has workspaces - redirect to their last workspace or first one
              const workspaceId = data.user?.last_workspace_id || data.workspaces[0]._id
              router.push(`/workspace/${workspaceId}/dashboard`)
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

    handleRedirect()
  }, [user, loading, router])

  return <>{children}</>
}