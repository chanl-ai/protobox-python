"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Edit, Play, Copy, Trash2, ArrowLeft } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { getPrompt, deletePrompt, type Prompt } from "@/lib/api/prompts"
import { LoadingState } from "@/components/ui/loading-state"
import { useWorkspaceReady } from "@/hooks/useWorkspaceReady"

export default function PromptDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const { workspaceId } = useWorkspaceReady()
  const promptId = params.promptId as string

  const [prompt, setPrompt] = useState<Prompt | null>(null)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (promptId) {
      // Redirect to edit page for now since that's the main interface
      router.replace(`/dashboard/prompts/${promptId}/edit`)
    }
  }, [promptId, router])

  const loadPrompt = async () => {
    try {
      setLoading(true)
      if (!workspaceId) return
      const data = await getPrompt(workspaceId, promptId)
      setPrompt(data)
    } catch (error) {
      console.error("Failed to load prompt:", error)
      toast({
        title: "Error",
        description: "Failed to load prompt details",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = () => {
    router.push(`/dashboard/prompts/${promptId}/edit`)
  }

  const handleDelete = async () => {
    if (!prompt || !confirm(`Are you sure you want to delete "${prompt.name}"?`)) {
      return
    }

    try {
      setDeleting(true)
      if (!workspaceId) return
      await deletePrompt(workspaceId, promptId)
      toast({
        title: "Success",
        description: "Prompt deleted successfully",
      })
      router.push("/dashboard/prompts")
    } catch (error) {
      console.error("Failed to delete prompt:", error)
      toast({
        title: "Error",
        description: "Failed to delete prompt",
        variant: "destructive",
      })
    } finally {
      setDeleting(false)
    }
  }

  const handleCopy = async () => {
    if (!prompt) return

    try {
      const promptText = prompt.messages.map(msg => 
        `${msg.role}: ${msg.content}`
      ).join('\n\n')
      
      await navigator.clipboard.writeText(promptText)
      toast({
        title: "Copied",
        description: "Prompt content copied to clipboard",
      })
    } catch (error) {
      console.error("Failed to copy:", error)
      toast({
        title: "Error",
        description: "Failed to copy prompt content",
        variant: "destructive",
      })
    }
  }

  if (loading) {
    return <LoadingState message="Loading prompt details..." />
  }

  if (!prompt) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <h2 className="text-2xl font-bold mb-2">Prompt Not Found</h2>
        <p className="text-muted-foreground mb-4">
          The prompt you're looking for doesn't exist or has been deleted.
        </p>
        <Button onClick={() => router.push("/dashboard/prompts")} variant="outline">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Prompts
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => router.push("/dashboard/prompts")}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{prompt.name}</h1>
            {prompt.description && (
              <p className="text-muted-foreground mt-1">{prompt.description}</p>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleCopy}>
            <Copy className="h-4 w-4 mr-2" />
            Copy
          </Button>
          <Button variant="outline" onClick={handleEdit}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button 
            variant="destructive" 
            onClick={handleDelete}
            disabled={deleting}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            {deleting ? "Deleting..." : "Delete"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Messages */}
          <Card>
            <CardHeader>
              <CardTitle>Messages</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {prompt.messages.map((message, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant={message.role === 'system' ? 'default' : 'secondary'}>
                      {message.role}
                    </Badge>
                  </div>
                  <div className="text-sm whitespace-pre-wrap font-mono bg-muted/30 p-3 rounded">
                    {message.content}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Arguments */}
          {prompt.arguments && prompt.arguments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Arguments ({prompt.arguments.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {prompt.arguments.map((arg, index) => (
                    <div key={index} className="border rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-medium text-sm">{arg.name}</span>
                        <Badge variant="outline" className="text-xs">
                          {arg.type}
                        </Badge>
                        {arg.required && (
                          <Badge variant="destructive" className="text-xs">
                            required
                          </Badge>
                        )}
                      </div>
                      {arg.description && (
                        <p className="text-xs text-muted-foreground mb-1">
                          {arg.description}
                        </p>
                      )}
                      {arg.default !== undefined && arg.default !== null && arg.default !== '' && (
                        <p className="text-xs text-muted-foreground">
                          Default: {String(arg.default)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Metadata */}
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium">Category</label>
                <p className="text-sm text-muted-foreground">
                  {prompt.category || 'Uncategorized'}
                </p>
              </div>
              
              {prompt.tags && prompt.tags.length > 0 && (
                <div>
                  <label className="text-sm font-medium">Tags</label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {prompt.tags.map((tag, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <Separator />

              <div>
                <label className="text-sm font-medium">Version</label>
                <p className="text-sm text-muted-foreground">v{prompt.version}</p>
              </div>

              <div>
                <label className="text-sm font-medium">Status</label>
                <div className="mt-1">
                  <Badge variant={prompt.is_active ? "default" : "secondary"}>
                    {prompt.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </div>

              {prompt.usage_count !== undefined && (
                <div>
                  <label className="text-sm font-medium">Usage Count</label>
                  <p className="text-sm text-muted-foreground">{prompt.usage_count}</p>
                </div>
              )}

              <Separator />

              <div>
                <label className="text-sm font-medium">Created</label>
                <p className="text-sm text-muted-foreground">
                  {new Date(prompt.created_at).toLocaleDateString()}
                </p>
              </div>

              <div>
                <label className="text-sm font-medium">Updated</label>
                <p className="text-sm text-muted-foreground">
                  {new Date(prompt.updated_at).toLocaleDateString()}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}