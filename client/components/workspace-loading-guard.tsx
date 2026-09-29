"use client"

import React, { useEffect, useState } from 'react'
import { useAuth } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, AlertCircle, LogOut, RefreshCw, Wifi, WifiOff } from "lucide-react"
import { useRouter } from "next/navigation"

interface WorkspaceLoadingGuardProps {
  children: React.ReactNode
}

export function WorkspaceLoadingGuard({ children }: WorkspaceLoadingGuardProps) {
  const { 
    user, 
    signOut,
    currentWorkspace, 
    workspaces, 
    workspaceLoading,
    loading: authLoading,
    error, 
    refreshWorkspaces 
  } = useAuth()
  const router = useRouter()
  const [hasRedirected, setHasRedirected] = useState(false)
  
  // Combine loading states
  const loading = authLoading || workspaceLoading
  
  // Check if current workspace needs onboarding and redirect
  useEffect(() => {
    if (!hasRedirected && currentWorkspace) {
      const needsOnboarding = currentWorkspace.settings?.needs_onboarding === true
      if (needsOnboarding) {
        // Redirect to onboarding page for workspaces that need setup
        setHasRedirected(true)
        router.push('/onboarding')
      }
    }
  }, [currentWorkspace, router, hasRedirected])
  
  // Redirect to onboarding if no workspaces exist
  useEffect(() => {
    // Only redirect if we're not loading, have no error, and workspaces array exists and is empty
    // Also check that we haven't already redirected
    if (!hasRedirected && !loading && !error && workspaces && Array.isArray(workspaces) && workspaces.length === 0) {
      setHasRedirected(true)
      router.push('/onboarding')
    }
  }, [loading, error, workspaces, router, hasRedirected])

  // Auth loading state
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <Card className="w-96">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
            <CardTitle>Authenticating</CardTitle>
            <CardDescription>Verifying your credentials...</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  // Workspace loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <Card className="w-96">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
            <CardTitle>Loading Workspace</CardTitle>
            <CardDescription>Setting up your environment...</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  // Handle errors first - show error state instead of redirecting
  if (error && !loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <Card className="w-96">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900">
              <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <CardTitle>Connection Error</CardTitle>
            <CardDescription>
              {error === "Request failed with status 500" 
                ? "The server encountered an error. Please try again."
                : error || "Unable to connect to the server."}
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <div className="space-y-2">
              <Button 
                onClick={refreshWorkspaces}
                className="w-full"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
              <Button 
                variant="outline" 
                onClick={() => signOut()}
                className="w-full"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Sign Out
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // No workspaces found AND no error - show redirecting message
  // The actual redirect happens in the useEffect above
  if (!loading && !error && workspaces && Array.isArray(workspaces) && workspaces.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <Card className="w-96">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
            </div>
            <CardTitle>Welcome!</CardTitle>
            <CardDescription>Redirecting to workspace setup...</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  // Invalid workspace state - system error
  if (!loading && workspaces.length > 0 && !currentWorkspace) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <Card className="w-96">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900">
              <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <CardTitle>Workspace Error</CardTitle>
            <CardDescription>
              Unable to load your workspace. This might be a temporary issue.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Found {workspaces.length} workspace{workspaces.length !== 1 ? 's' : ''} but unable to select one.
            </div>
            <div className="space-y-2">
              <Button 
                onClick={refreshWorkspaces}
                className="w-full"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Retry
              </Button>
              <Button 
                variant="outline" 
                onClick={() => {
                }}
                className="w-full"
              >
                Debug Info
              </Button>
              <Button 
                variant="outline" 
                onClick={() => signOut()}
                className="w-full"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Sign Out & Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // All good - render the dashboard
  return <>{children}</>
}