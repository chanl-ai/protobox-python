"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  History, 
  GitBranch, 
  Eye, 
  RotateCcw, 
  MoreVertical,
  User,
  Calendar,
  MessageSquare,
  Loader2
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { toast } from "sonner"
import { promptsApi, PromptVersion as APIPromptVersion } from "@/lib/api/prompts"

// Use the PromptVersion type from the API
type PromptVersion = APIPromptVersion & {
  is_current?: boolean
}

interface VersionHistoryDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  prompt: {
    id: string
    name: string
    description: string
    workspace_id?: string
  }
  onRestore?: (versionId: string) => void
  onView?: (versionId: string) => void
}

export function VersionHistoryDialog({ 
  open, 
  onOpenChange, 
  prompt, 
  onRestore, 
  onView 
}: VersionHistoryDialogProps) {
  const [versions, setVersions] = useState<PromptVersion[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<PromptVersion | null>(null)
  const [currentVersion, setCurrentVersion] = useState<number>(1)


  useEffect(() => {
    if (open) {
      loadVersions()
    }
  }, [open])

  const loadVersions = async () => {
    // Try to get workspace ID from prompt or localStorage
    const workspaceId = prompt.workspace_id || localStorage.getItem('lastWorkspaceId')
    
    if (!workspaceId) {
      toast.error("No workspace selected")
      return
    }
    
    setLoading(true)
    try {
      const response = await promptsApi.getPromptVersions(workspaceId, prompt.id)
      
      // Mark the current version
      const versionsWithCurrent = response.versions.map(v => ({
        ...v,
        is_current: v.version === response.current_version
      }))
      
      setVersions(versionsWithCurrent)
      setCurrentVersion(response.current_version)
    } catch (error) {
      console.error("Failed to load version history:", error)
      toast.error("Failed to load version history")
    } finally {
      setLoading(false)
    }
  }

  const handleRestore = async (version: PromptVersion) => {
    // Try to get workspace ID from prompt or localStorage
    const workspaceId = prompt.workspace_id || localStorage.getItem('lastWorkspaceId')
    
    if (!workspaceId) {
      toast.error("No workspace selected")
      return
    }
    
    try {
      await promptsApi.restorePromptVersion(workspaceId, prompt.id, version.version)
      
      toast.success(`Restored to version ${version.version}`)
      onRestore?.(version.id)
      onOpenChange(false)
    } catch (error) {
      console.error("Failed to restore version:", error)
      toast.error("Failed to restore version")
    }
  }

  const handleView = (version: PromptVersion) => {
    setSelectedVersion(version)
    onView?.(version.id)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const getVersionColor = (version: number) => {
    const colors = [
      "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
      "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
      "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300",
      "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-300",
      "bg-rose-100 text-rose-800 dark:bg-rose-900 dark:text-rose-300"
    ]
    return colors[(version - 1) % colors.length]
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Version History: {prompt.name}
          </DialogTitle>
          <DialogDescription>
            View and manage different versions of this prompt
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin" />
            </div>
          ) : (
            <ScrollArea className="h-[400px]">
              <div className="space-y-4">
                {versions.map((version, index) => (
                  <Card key={version.id} className={version.is_current ? "ring-2 ring-primary" : ""}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <GitBranch className="h-4 w-4 text-muted-foreground" />
                          <div>
                            <CardTitle className="text-lg flex items-center gap-2">
                              Version {version.version}
                              {version.is_current && (
                                <Badge variant="default">Current</Badge>
                              )}
                            </CardTitle>
                            <CardDescription>{version.change_summary || "No description"}</CardDescription>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={getVersionColor(version.version)}>
                            {version.version}
                          </Badge>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="sm">
                                <MoreVertical className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuLabel>Actions</DropdownMenuLabel>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem onClick={() => handleView(version)}>
                                <Eye className="h-4 w-4 mr-2" />
                                View Details
                              </DropdownMenuItem>
                              {!version.is_current && (
                                <DropdownMenuItem onClick={() => handleRestore(version)}>
                                  <RotateCcw className="h-4 w-4 mr-2" />
                                  Restore Version
                                </DropdownMenuItem>
                              )}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <User className="h-3 w-3" />
                            {version.created_by}
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(version.created_at)}
                          </div>
                          <div className="flex items-center gap-1">
                            <MessageSquare className="h-3 w-3" />
                            {version.messages.length} message{version.messages.length !== 1 ? 's' : ''}
                          </div>
                        </div>
                        
                        {version.arguments.length > 0 && (
                          <div>
                            <p className="text-sm font-medium mb-1">Arguments:</p>
                            <div className="flex flex-wrap gap-1">
                              {version.arguments.map((arg) => (
                                <Badge key={arg.name} variant="outline" className="text-xs">
                                  {arg.name} ({arg.type})
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          )}

          {/* Selected Version Details */}
          {selectedVersion && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="h-4 w-4" />
                  Version {selectedVersion.version} Details
                </CardTitle>
                <CardDescription>{selectedVersion.change_summary}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">Messages:</h4>
                  <div className="space-y-2">
                    {selectedVersion.messages.map((message, index) => (
                      <div key={index} className="p-3 bg-muted rounded-md">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline" className="text-xs">
                            {message.role.toUpperCase()}
                          </Badge>
                        </div>
                        <pre className="text-sm whitespace-pre-wrap">{message.content}</pre>
                      </div>
                    ))}
                  </div>
                </div>
                
                {selectedVersion.arguments.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">Arguments:</h4>
                    <div className="space-y-2">
                      {selectedVersion.arguments.map((arg) => (
                        <div key={arg.name} className="p-2 border rounded-md">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium">{arg.name}</span>
                            <Badge variant="outline" className="text-xs">
                              {arg.type}
                            </Badge>
                            {arg.required && (
                              <Badge variant="destructive" className="text-xs">
                                Required
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground">{arg.description}</p>
                          {arg.default && (
                            <p className="text-xs text-muted-foreground">
                              Default: {arg.default}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
