"use client"

import { useEffect, useState, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useAuthStore } from "@/lib/auth/stores/auth.store"
import { useAuth } from "@/lib/auth"
import { tokenManager } from "@/lib/auth/token-manager"
import { LoginForm } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import Link from "next/link"
import { AuthFormWrapper } from "@/components/auth/auth-form-wrapper"
import { logger } from "@/lib/logger"
import { Card, CardHeader, CardContent, CardFooter, CardTitle, CardDescription } from "@/components/ui/card"
import { Shield, CheckCircle, AlertCircle, Loader2 } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useWorkspaces } from "@/lib/api/hooks/use-workspaces"

function OAuthAuthorizeContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user, loading: authLoading, isAuthenticated } = useAuth()
  const [showConsent, setShowConsent] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [clientInfo, setClientInfo] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const { data: workspacesData } = useWorkspaces()
  const workspaces = workspacesData?.workspaces ?? []
  const [workspaceId, setWorkspaceId] = useState<string>("")

  useEffect(() => {
    if (!workspaceId && workspaces.length) setWorkspaceId(workspaces[0].id)
  }, [workspaces, workspaceId])
  
  // Extract OAuth parameters from URL
  const oauthParams = {
    response_type: searchParams.get("response_type") || "",
    client_id: searchParams.get("client_id") || "",
    redirect_uri: searchParams.get("redirect_uri") || "",
    scope: searchParams.get("scope") || "",
    state: searchParams.get("state") || "",
    code_challenge: searchParams.get("code_challenge") || "",
    code_challenge_method: searchParams.get("code_challenge_method") || "",
  }

  useEffect(() => {
    // Check authentication state
    logger.log('[OAuth] Auth state:', { isAuthenticated, hasUser: !!user, loading: authLoading })
    
    // If user is already authenticated, show consent screen
    if (!authLoading && isAuthenticated && user) {
      logger.log('[OAuth] User authenticated, showing consent screen')
      setShowConsent(true)
      // TODO: Fetch client info based on client_id
      // TODO: Validate workspace matches OAuth client expectations
      setClientInfo({
        name: "MCP Client Application",
        description: "Requesting access to your workspace",
        workspace_id: oauthParams.client_id?.split('_')[1] // Extract workspace from client_id if present
      })
    }
  }, [isAuthenticated, user, authLoading, oauthParams.client_id])

  const handleLoginSuccess = async (user: any) => {
    logger.log('[OAuth] Login successful for user:', user?.email)
    // After login, show consent screen
    setShowConsent(true)
    setClientInfo({
      name: "MCP Client Application",
      description: "Requesting access to your workspace",
      workspace_id: oauthParams.client_id?.split('_')[1] // Extract workspace from client_id if present
    })
    // The auth state will update automatically, no need to manually update
  }

  const handleConsent = async (approved: boolean) => {
    setIsProcessing(true)
    
    try {
      if (!approved) {
        // User denied - redirect back with error
        const redirectUrl = new URL(oauthParams.redirect_uri)
        redirectUrl.searchParams.set('error', 'access_denied')
        redirectUrl.searchParams.set('error_description', 'User denied authorization')
        if (oauthParams.state) {
          redirectUrl.searchParams.set('state', oauthParams.state)
        }
        window.location.href = redirectUrl.toString()
        return
      }

      // Get the access token from tokenManager (single source of truth)
      const token = tokenManager.getToken()
      
      // Also check auth store state for debugging
      const authState = useAuthStore.getState()
      
      logger.log('[OAuth] Auth state:', {
        isAuthenticated: authState.isAuthenticated,
        hasUser: !!authState.user,
        hasCustomToken: !!authState.customToken,
        hasFirebaseUser: !!authState.firebaseUser
      })
      logger.log('[OAuth] Token from tokenManager:', token ? 'Present' : 'Missing')
      logger.log('[OAuth] Token preview:', token ? token.substring(0, 30) + '...' : 'N/A')
      logger.log('[OAuth] Custom token from auth store:', authState.customToken ? 'Present' : 'Missing')
      
      if (!token) {
        throw new Error("No authentication token found")
      }

      // Submit authorization decision to backend programmatic endpoint
      const response = await fetch('/api/oauth/authorize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          client_id: oauthParams.client_id,
          redirect_uri: oauthParams.redirect_uri,
          scope: oauthParams.scope,
          code_challenge: oauthParams.code_challenge,
          code_challenge_method: oauthParams.code_challenge_method,
          state: oauthParams.state,
          workspace_id: workspaceId,
          action: 'approve',
        }),
      })

      if (!response.ok) {
        const failure = await response.json().catch(() => ({})) as { detail?: string }
        throw new Error(failure.detail || 'Authorization failed')
      }

      const result = await response.json() as { redirect_uri?: string; error?: string }
      
      if (result.error) {
        throw new Error(result.error)
      }

      if (result.redirect_uri) {
        window.location.href = result.redirect_uri
      } else {
        // Fallback redirect
        const redirectUrl = new URL(oauthParams.redirect_uri)
        redirectUrl.searchParams.set('code', 'temp_code')
        if (oauthParams.state) {
          redirectUrl.searchParams.set('state', oauthParams.state)
        }
        window.location.href = redirectUrl.toString()
      }
    } catch (error) {
      logger.error('[OAuth] Authorization error:', error)
      // Redirect with error
      const redirectUrl = new URL(oauthParams.redirect_uri)
      redirectUrl.searchParams.set('error', 'server_error')
      redirectUrl.searchParams.set('error_description', 'Internal error')
      if (oauthParams.state) {
        redirectUrl.searchParams.set('state', oauthParams.state)
      }
      window.location.href = redirectUrl.toString()
    } finally {
      setIsProcessing(false)
    }
  }

  // Parse scopes for display
  const requestedScopes = oauthParams.scope.split(" ").filter(Boolean)
  
  // Show loading while auth is being checked
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <h2 className="mt-4 text-lg font-semibold">Loading...</h2>
        </div>
      </div>
    )
  }
  
  // If not authenticated, show login form
  if (!showConsent) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-4xl">
          <AuthFormWrapper>
            <div className="mb-6 text-center">
              <h2 className="text-2xl font-bold mb-2">OAuth Authorization</h2>
              <p className="text-sm text-muted-foreground">
                Sign in to authorize the application
              </p>
            </div>
            <LoginForm
              brandName="ProtoBox"
              components={{
                Button,
                Input,
                Label,
                Link: Link as any
              }}
              showSocialAuth={true}
              showPasswordReset={false}
              onSuccess={handleLoginSuccess}
            />
          </AuthFormWrapper>
        </div>
      </div>
    )
  }

  // Show consent screen
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Shield className="h-12 w-12 text-primary" />
          </div>
          <CardTitle className="text-2xl">Authorize Access</CardTitle>
          <CardDescription>
            {clientInfo?.description || "An application is requesting access to your account"}
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* User info */}
          <div className="text-center p-3 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">Signed in as</p>
            <p className="font-medium">{user?.email}</p>
          </div>

          {/* The access token is bound to one workspace you belong to */}
          <div className="space-y-2">
            <Label htmlFor="oauth-workspace">Workspace</Label>
            <Select value={workspaceId} onValueChange={setWorkspaceId}>
              <SelectTrigger id="oauth-workspace">
                <SelectValue placeholder="Choose a workspace" />
              </SelectTrigger>
              <SelectContent>
                {workspaces.map((ws: { id: string; name: string }) => (
                  <SelectItem key={ws.id} value={ws.id}>{ws.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Client info */}
          <div className="space-y-2">
            <h3 className="font-semibold flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {clientInfo?.name || "Application"}
            </h3>
            <p className="text-sm text-muted-foreground">
              is requesting the following permissions:
            </p>
          </div>

          {/* Requested permissions */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium">Permissions requested:</h4>
            <div className="space-y-2">
              {requestedScopes.includes("mcp:read") && (
                <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium text-sm">Read workspace data</p>
                    <p className="text-xs text-muted-foreground">
                      View actions, configurations, and workspace information
                    </p>
                  </div>
                </div>
              )}
              
              {requestedScopes.includes("mcp:write") && (
                <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium text-sm">Modify workspace data</p>
                    <p className="text-xs text-muted-foreground">
                      Create and update actions, settings, and configurations
                    </p>
                  </div>
                </div>
              )}
              
              {requestedScopes.includes("mcp:execute") && (
                <div className="flex items-start gap-3 p-3 bg-muted/50 rounded-lg">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <div className="flex-1">
                    <p className="font-medium text-sm">Execute actions</p>
                    <p className="text-xs text-muted-foreground">
                      Run MCP tools and actions in your workspace
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 rounded-lg">
            <p className="text-xs text-amber-800 dark:text-amber-200">
              By authorizing, you allow this application to access your workspace 
              with the permissions listed above. You can revoke this authorization at any 
              time from your workspace settings.
            </p>
          </div>
        </CardContent>
        
        <CardFooter className="flex gap-3">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => handleConsent(false)}
            disabled={isProcessing}
          >
            Deny
          </Button>
          <Button
            className="flex-1"
            onClick={() => handleConsent(true)}
            disabled={isProcessing}
          >
            {isProcessing ? "Processing..." : "Authorize"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}

export default function OAuthAuthorizePage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <h2 className="mt-4 text-lg font-semibold">Loading...</h2>
        </div>
      </div>
    }>
      <OAuthAuthorizeContent />
    </Suspense>
  )
}