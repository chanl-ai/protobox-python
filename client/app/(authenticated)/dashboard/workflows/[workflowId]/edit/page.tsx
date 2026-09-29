"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { useWorkspaceReady } from "@/hooks"
import { type Workflow } from "@/lib/api/workflows"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { TagsInput } from "@/components/ui/tags-input"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { toast } from "sonner"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { 
  Save, 
  Loader2,
  Settings,
  Play,
  Workflow as WorkflowIcon
} from "lucide-react"
import { WorkflowEditor } from "@/components/workflows/workflow-editor"

// Form validation schema for workflows
const workflowFormSchema = z.object({
  name: z.string()
    .min(1, "Workflow name is required")
    .max(255, "Name must be 255 characters or less")
    .regex(/^[a-zA-Z0-9\s\-_]+$/, "Name can only contain letters, numbers, spaces, hyphens, and underscores"),
  description: z.string()
    .min(10, "Description must be at least 10 characters")
    .max(1000, "Description must be 1000 characters or less"),
  tags: z.array(z.string()).default([]),
  version: z.string()
    .regex(/^\d+\.\d+\.\d+$/, "Version must follow semantic versioning (e.g., 1.0.0)"),
})

type WorkflowFormData = z.infer<typeof workflowFormSchema>

// Common tag suggestions for workflows
const commonWorkflowTags = [
  "automation", "workflow", "pipeline", "integration", "data-processing", 
  "notification", "email", "scheduling", "monitoring", "reporting",
  "approval", "review", "validation", "transformation", "sync",
  "backup", "cleanup", "maintenance", "onboarding", "offboarding"
]

export default function WorkflowEditPage() {
  const params = useParams()
  const router = useRouter()
  const { user } = useAuth()
  const { isReady, workspaceId } = useWorkspaceReady()
  const workflowId = params.workflowId as string
  
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false)

  // Form setup
  const form = useForm({
    resolver: zodResolver(workflowFormSchema),
    defaultValues: {
      name: "",
      description: "",
      tags: [],
      version: "1.0.0",
    }
  })

  // Mock workflow data for now
  useEffect(() => {
    if (!workspaceId || !workflowId) return
    
    // Mock workflow data
    const mockWorkflow: Workflow = {
      id: workflowId,
      name: `Workflow ${workflowId}`,
      description: 'This is a mock workflow for UI development',
      version: '1.0.0',
      tags: ['mock', 'development'],
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      workspace_id: workspaceId
    }
    
    setWorkflow(mockWorkflow)
    form.reset({
      name: mockWorkflow.name,
      description: mockWorkflow.description || "",
      tags: mockWorkflow.tags,
      version: mockWorkflow.version,
    })
    setLoading(false)
  }, [workspaceId, workflowId, form])

  const onSubmit = async (data: WorkflowFormData) => {
    if (!workspaceId || !workflow) return

    setSaving(true)
    try {
      // Mock update - just update local state
      const updatedWorkflow = { ...workflow, ...data }
      setWorkflow(updatedWorkflow)
      toast.success('Workflow updated successfully')
      setSettingsDialogOpen(false)
    } catch (error) {
      toast.error('Failed to update workflow')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveWorkflow = () => {
    // Save the workflow configuration
    console.log('Saving workflow configuration')
    toast.success('Workflow configuration saved')
  }

  const handleTestWorkflow = () => {
    // Test the workflow
    console.log('Testing workflow')
    toast.success('Workflow test completed')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (!workflow) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Workflow not found</p>
      </div>
    )
  }

  return (
    <div className="container mx-auto space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <WorkflowIcon className="h-8 w-8 text-muted-foreground" />
          <div>
            <h1 className="text-3xl font-bold">{workflow.name}</h1>
            <p className="text-muted-foreground">Design and configure your automated workflow</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Settings Button */}
          <Dialog open={settingsDialogOpen} onOpenChange={setSettingsDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-2xl">
              <DialogHeader>
                <DialogTitle>Workflow Settings</DialogTitle>
                <DialogDescription>
                  Update workflow name, description, and metadata
                </DialogDescription>
              </DialogHeader>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Enter workflow name" {...field} />
                        </FormControl>
                        <FormDescription>
                          A descriptive name for your workflow
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder="Describe what this workflow does"
                            className="min-h-[80px]"
                            {...field} 
                          />
                        </FormControl>
                        <FormDescription>
                          Explain the purpose and functionality of this workflow
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={form.control}
                    name="version"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Version</FormLabel>
                        <FormControl>
                          <Input placeholder="1.0.0" {...field} />
                        </FormControl>
                        <FormDescription>
                          Semantic version for this workflow
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={form.control}
                    name="tags"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Tags</FormLabel>
                        <FormControl>
                          <TagsInput
                            value={field.value}
                            onChange={field.onChange}
                            placeholder="e.g., automation, data-sync, daily"
                            suggestions={commonWorkflowTags}
                          />
                        </FormControl>
                        <FormDescription>
                          Add tags to categorize and filter workflows
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <div className="flex justify-end gap-2 pt-4">
                    <Button 
                      type="button" 
                      variant="outline" 
                      onClick={() => setSettingsDialogOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button type="submit" disabled={saving}>
                      {saving ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Save className="h-4 w-4 mr-2" />
                      )}
                      Save Changes
                    </Button>
                  </div>
                </form>
              </Form>
            </DialogContent>
          </Dialog>

          {/* Test Button */}
          <Button variant="outline" onClick={handleTestWorkflow}>
            <Play className="mr-2 h-4 w-4" />
            Test
          </Button>

          {/* Save Button */}
          <Button onClick={handleSaveWorkflow}>
            <Save className="mr-2 h-4 w-4" />
            Save
          </Button>
        </div>
      </div>

      {/* Full-width Workflow Editor */}
      <div className="h-[calc(100vh-200px)] border rounded-lg">
        <WorkflowEditor
          workflow={workflow?.config_schema?.workflow}
          onSave={(workflowConfig) => {
            // Update the workflow configuration
            console.log('Saving workflow config:', workflowConfig)
            // This would typically update the workflow's config_schema
          }}
          onTest={() => {
            // Test the workflow
            console.log('Testing workflow')
          }}
        />
      </div>
    </div>
  )
}
