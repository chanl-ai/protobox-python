"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { AlertCircle, Plus } from "lucide-react"
import { useRouter } from "next/navigation"

interface WorkspaceSelectionPromptProps {
  error?: string | null
  hasWorkspaces?: boolean
}

export function WorkspaceSelectionPrompt({ 
  error, 
  hasWorkspaces = false 
}: WorkspaceSelectionPromptProps) {
  const router = useRouter()

  const handleCreateWorkspace = () => {
    router.push('/onboarding')
  }

  const handleRetry = () => {
    window.location.reload()
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertCircle className="h-6 w-6 text-destructive" />
            </div>
            <CardTitle>Workspace Error</CardTitle>
            <CardDescription>
              There was a problem loading your workspaces
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
            
            <div className="flex flex-col gap-2">
              <Button onClick={handleRetry}>
                Try Again
              </Button>
              <Button variant="outline" onClick={handleCreateWorkspace}>
                Create New Workspace
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
            <Plus className="h-6 w-6 text-primary" />
          </div>
          <CardTitle>
            {hasWorkspaces ? 'Select a Workspace' : 'Create Your First Workspace'}
          </CardTitle>
          <CardDescription>
            {hasWorkspaces 
              ? 'Choose a workspace to continue working' 
              : 'Get started by creating your first workspace'
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button 
            onClick={handleCreateWorkspace} 
            className="w-full"
            size="lg"
          >
            <Plus className="h-4 w-4 mr-2" />
            {hasWorkspaces ? 'Create New Workspace' : 'Create Workspace'}
          </Button>
          
          {hasWorkspaces && (
            <Button 
              variant="outline" 
              onClick={handleRetry}
              className="w-full mt-2"
            >
              Refresh Workspaces
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}