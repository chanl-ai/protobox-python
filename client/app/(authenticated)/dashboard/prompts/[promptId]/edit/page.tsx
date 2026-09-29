"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { useWorkspaceReady } from "@/hooks/useWorkspaceReady"
import { promptsApi } from "@/lib/api/prompts"
import { Button } from "@/components/ui/button"
import { LoadingState } from "@/components/ui/loading-state"
import { PromptEditForm, PromptEditFormRef } from "@/components/prompts/prompt-edit-form"
import { PromptStats } from "@/components/prompts/prompt-stats"
import { PromptArgumentsPanel } from "@/components/prompts/prompt-arguments-panel"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { PreviewPromptDialog } from "@/components/prompts/preview-prompt-dialog"
import { DuplicatePromptDialog } from "@/components/prompts/duplicate-prompt-dialog"
import { VersionHistoryDialog } from "@/components/prompts/version-history-dialog"
import { 
  ArrowLeft, 
  Eye, 
  Trash2, 
  FileText,
  MoreVertical,
  Copy,
  History
} from "lucide-react"
import { toast } from "sonner"

// Import API types
import { Prompt, PromptMessage, PromptArgument, PromptUpdateRequest } from "@/lib/api/prompts"

// Helper function to convert messages to content string
const messagesToContent = (messages: PromptMessage[] | undefined): string => {
  return messages?.map((m: PromptMessage) => `${m.role}: ${m.content}`).join('\n\n') || ''
}

// Helper function to convert content string to messages array
const contentToMessages = (content: string): PromptMessage[] => {
  return [
    { role: "system" as const, content: content || "You are a helpful assistant." }
  ]
}

// Helper function to extract variable names from content using {{variable}} pattern
const extractVariablesFromContent = (content: string): string[] => {
  // Only match complete {{variable}} patterns with both opening and closing braces
  const regex = /\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}/g
  const variables: string[] = []
  let match
  
  while ((match = regex.exec(content)) !== null) {
    const variable = match[1]
    if (!variables.includes(variable)) {
      variables.push(variable)
    }
  }
  
  return variables
}

export default function EditPromptPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  
  // State management
  const [prompt, setPrompt] = useState<Prompt | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [formDirty, setFormDirty] = useState(false)
  const [promptArguments, setPromptArguments] = useState<PromptArgument[]>([])
  const [detectedArguments, setDetectedArguments] = useState<string[]>([])
  // Form ref for external submit
  const formRef = useRef<PromptEditFormRef>(null)
  
  // Dialog states
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false)
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false)
  const [versionHistoryDialogOpen, setVersionHistoryDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)

  // Get workspace context
  const { isReady, workspaceId } = useWorkspaceReady()

  // Load prompt data
  useEffect(() => {
    const loadPrompt = async () => {
      if (!params.promptId || !workspaceId || !isReady) return
      
      setLoading(true)
      setError(null)
      
      try {
        const response = await promptsApi.getPrompt(workspaceId, params.promptId as string)
        setPrompt(response)
        
        // Initialize arguments state
        setPromptArguments(response.arguments || [])
        
        // Detect variables in content
        const content = messagesToContent(response.messages)
        const detected = extractVariablesFromContent(content)
        setDetectedArguments(detected)
      } catch (error) {
        console.error('Failed to load prompt:', error)
        setError('Failed to load prompt. Please try again.')
      } finally {
        setLoading(false)
      }
    }

    loadPrompt()
  }, [params.promptId, isReady, workspaceId])

  // Convert prompt data to form format
  const getFormData = (): { name: string; description: string; content: string; tags: string[]; arguments: PromptArgument[] } | null => {
    if (!prompt) return null
    
    return {
      name: prompt.name || "",
      description: prompt.description || "",
      content: messagesToContent(prompt.messages),
      tags: prompt.tags || [],
      arguments: promptArguments
    }
  }

  // Handle form submission
  const handleSubmit = async (data: { name: string; description: string; content: string; tags: string[]; arguments: PromptArgument[] }) => {
    if (!workspaceId || !prompt) return
    
    setSaving(true)
    try {
      const updateData: PromptUpdateRequest = {
        name: data.name,
        description: data.description,
        category: prompt.category || "General", // Keep existing category or default to General
        tags: data.tags,
        messages: contentToMessages(data.content),
        arguments: data.arguments || [],
        is_active: prompt.is_active || true,
      }
      
      const updatedPrompt = await promptsApi.updatePrompt(workspaceId, params.promptId as string, updateData)
      setPrompt(updatedPrompt)
      setFormDirty(false)
      toast.success("Prompt updated successfully")
      // Stay on the page instead of navigating away
    } catch (error) {
      console.error('Failed to update prompt:', error)
      toast.error("Failed to update prompt")
    } finally {
      setSaving(false)
    }
  }

  // Handle form cancellation
  const handleCancel = () => {
    router.back()
  }

  const handleDeleteClick = () => {
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!workspaceId) {
      toast.error("No workspace selected")
      return
    }

    try {
      await promptsApi.deletePrompt(workspaceId, params.promptId as string)
      
      toast.success("Prompt deleted successfully")
      router.push(`/dashboard/prompts`)
    } catch (error) {
      console.error('Failed to delete prompt:', error)
      toast.error("Failed to delete prompt")
    } finally {
      setDeleteDialogOpen(false)
    }
  }

  const handlePreview = () => {
    setPreviewDialogOpen(true)
  }

  const handleDuplicate = () => {
    setDuplicateDialogOpen(true)
  }

  const handleExport = () => {
    if (!prompt) return
    
    const promptText = messagesToContent(prompt.messages)
    const content = `# ${prompt.name}\n\n${prompt.description}\n\n## Prompt Content\n\n${promptText}\n\n## Tags\n\n${prompt.tags?.join(', ') || 'None'}\n\n## Category\n\n${prompt.category || 'General'}`
    
    // Create and download the file
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${prompt.name.replace(/[^a-z0-9]/gi, '_').toLowerCase()}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    
    toast.success('Prompt exported successfully')
  }

  const handleVersionHistory = () => {
    setVersionHistoryDialogOpen(true)
  }

  const handleDuplicateSuccess = () => {
    toast.success("Prompt duplicated successfully")
  }

  const handleSaveFromHeader = () => {
    if (formRef.current) {
      formRef.current.submitForm()
    }
  }

  const handleArgumentsChange = useCallback((newArguments: PromptArgument[]) => {
    setPromptArguments(newArguments)
    setFormDirty(true)
  }, [])

  const handleContentChange = useCallback((content: string) => {
    // Just scan for detected arguments, don't auto-add them
    const detected = extractVariablesFromContent(content)
    setDetectedArguments(detected)
  }, [])
  

  // Version selection removed - handled by Version History dialog

  // Early returns for different states
  if (!isReady) {
    return <LoadingState message="Initializing workspace..." />
  }

  if (loading) {
    return <LoadingState message="Loading prompt..." />
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-destructive mb-4">{error}</p>
          <Button onClick={() => window.location.reload()}>Try Again</Button>
        </div>
      </div>
    )
  }

  if (!prompt) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">Prompt not found</p>
          <Button onClick={() => router.push('/dashboard/prompts')}>Back to Prompts</Button>
        </div>
      </div>
    )
  }

  // Get form data once prompt is loaded
  const formData = getFormData()
  if (!formData) return <LoadingState message="Preparing form..." />

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/dashboard/prompts')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Edit Prompt</h1>
            <p className="text-muted-foreground">
              Modify your prompt settings and content
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Primary Action - Save Only */}
          <Button 
            variant="default" 
            size="sm" 
            onClick={handleSaveFromHeader}
            disabled={saving || !formDirty}
          >
            {saving ? "Saving..." : "Save Changes"}
          </Button>
          
          {/* All Other Actions in Overflow Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuSeparator />
              
              {/* Version Control */}
              {workspaceId && (
                <>
                  <DropdownMenuItem onClick={handleVersionHistory}>
                    <History className="h-4 w-4 mr-2" />
                    Version History
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                </>
              )}
              
              {/* Secondary Actions */}
              <DropdownMenuItem onClick={handlePreview}>
                <Eye className="h-4 w-4 mr-2" />
                Preview
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleDuplicate}>
                <Copy className="h-4 w-4 mr-2" />
                Duplicate
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleExport}>
                <FileText className="h-4 w-4 mr-2" />
                Export
              </DropdownMenuItem>
              
              <DropdownMenuSeparator />
              
              {/* Destructive Actions */}
              <DropdownMenuItem 
                onClick={handleDeleteClick}
                className="text-destructive focus:text-destructive"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Component-Driven Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Form - Using Component */}
        <div className="lg:col-span-2">
          <PromptEditForm
            ref={formRef}
            initialData={formData}
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            saving={saving}
            hideActions={true}
            onDirtyChange={setFormDirty}
            onArgumentsChange={handleArgumentsChange}
            onContentChange={handleContentChange}
          />
        </div>

        {/* Sidebar - Using Component */}
        <div className="space-y-6">
          <PromptArgumentsPanel
            arguments={promptArguments}
            onChange={handleArgumentsChange}
            detectedArguments={detectedArguments}
          />
          
          <PromptStats
            usageCount={prompt.usage_count || 0}
            status={prompt.is_active ? "Active" : "Draft"}
            createdAt={prompt.created_at}
            createdBy={prompt.created_by}
            updatedAt={prompt.updated_at}
          />
        </div>
      </div>

      {/* Dialogs */}
       <PreviewPromptDialog
         open={previewDialogOpen}
         onOpenChange={setPreviewDialogOpen}
         prompt={prompt ? {
           ...prompt,
           messages: prompt.messages || [],
           arguments: prompt.arguments || []
         } : undefined}
       />
      
      <DuplicatePromptDialog
        open={duplicateDialogOpen}
        onOpenChange={setDuplicateDialogOpen}
        prompt={prompt ? {
          ...prompt,
          messages: prompt.messages || [],
          arguments: prompt.arguments || []
        } : undefined}
        onSuccess={handleDuplicateSuccess}
      />
      
      
         <VersionHistoryDialog
           open={versionHistoryDialogOpen}
           onOpenChange={setVersionHistoryDialogOpen}
           prompt={{
             ...prompt,
             workspace_id: workspaceId || ""
           }}
           onRestore={() => {
             toast.success(`Version restored successfully`)
             // Reload the prompt data after restore
             if (workspaceId && params.promptId) {
               promptsApi.getPrompt(workspaceId, params.promptId as string)
                 .then(response => {
                   setPrompt(response)
                 })
                 .catch(error => console.error('Failed to reload prompt:', error))
             }
           }}
         />

         {/* Delete Confirmation Dialog */}
         <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
           <AlertDialogContent>
             <AlertDialogHeader>
               <AlertDialogTitle>Delete Prompt</AlertDialogTitle>
               <AlertDialogDescription>
                 Are you sure you want to permanently delete "{prompt?.name || 'this prompt'}"?
                 <br /><br />
                 This action cannot be undone. All versions will be deleted and any references will be broken.
               </AlertDialogDescription>
             </AlertDialogHeader>
             <AlertDialogFooter>
               <AlertDialogCancel>Cancel</AlertDialogCancel>
               <AlertDialogAction
                 onClick={handleDeleteConfirm}
                 className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
               >
                 Delete Prompt
               </AlertDialogAction>
             </AlertDialogFooter>
           </AlertDialogContent>
         </AlertDialog>
    </div>
  )
}
