"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { useWorkspaceReady } from "@/hooks"
import { type Workflow } from "@/lib/api/workflows"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { toast } from "sonner"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { 
  Plus,
  Loader2,
  Search,
  Filter,
  Play,
  Settings,
  Calendar,
  Clock,
  CheckCircle,
  AlertCircle,
  Workflow as WorkflowIcon
} from "lucide-react"
import { ActionTypeSelector } from "@/components/action-type-selector"
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
import { DataTable } from "@/components/common/data-table"
import { columns as workflowColumns } from "@/components/workflows/columns"
import { DataTableRowActions } from "@/components/workflows/data-table-row-actions"
import { DataTableToolbar } from "@/components/workflows/data-table-toolbar"
import { CreateWorkflowTemplateDialog } from "@/components/workflows/create-workflow-template-dialog"

// Workflow form schema
const workflowFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  version: z.string().default("1.0.0"),
  tags: z.string().optional(),
})

type WorkflowFormData = z.infer<typeof workflowFormSchema>

export default function WorkflowsPage() {
  const router = useRouter()
  const params = useParams()
  const { isReady, workspaceId, user, getDependencies } = useWorkspaceReady()
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [loading, setLoading] = useState(true)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)
  const [executing, setExecuting] = useState<string | null>(null)

  // Create form
  const createForm = useForm<WorkflowFormData>({
    resolver: zodResolver(workflowFormSchema) as any,
    defaultValues: {
      name: "",
      description: "",
      version: "1.0.0",
      tags: "",
    },
  })

  // Mock workflows data for now
  useEffect(() => {
    if (!isReady || !workspaceId) return

    // Mock workflows data
    const mockWorkflows: Workflow[] = [
      {
        id: '1',
        name: 'Daily Data Sync',
        description: 'Automatically sync data from external sources daily',
        version: '1.0.0',
        tags: ['automation', 'data-sync', 'daily'],
        status: 'active',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        workspace_id: workspaceId
      },
      {
        id: '2',
        name: 'User Onboarding',
        description: 'Automated workflow for new user onboarding process',
        version: '2.1.0',
        tags: ['automation', 'onboarding', 'user-management'],
        status: 'active',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        workspace_id: workspaceId
      },
      {
        id: '3',
        name: 'Monthly Report Generation',
        description: 'Generate and send monthly reports to stakeholders',
        version: '1.5.0',
        tags: ['reporting', 'monthly', 'automation'],
        status: 'scheduled',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        workspace_id: workspaceId
      }
    ]
    
    setWorkflows(mockWorkflows)
    setLoading(false)
  }, [isReady, workspaceId])

  // Calculate stats
  const stats = [
    {
      title: "Total Workflows",
      value: workflows.length.toString(),
      change: "+1 from last week",
    },
    {
      title: "Active Workflows",
      value: workflows.filter(w => w.status === "active").length.toString(),
      change: "+1 from last week",
    },
    {
      title: "Scheduled Workflows",
      value: "0",
      change: "No change",
    },
    {
      title: "Recent Executions",
      value: "0",
      change: "View all",
    },
  ]

  const handleCreateWorkflow = async (data: WorkflowFormData) => {
    try {
      // Mock workflow creation
      const newWorkflow: Workflow = {
        id: Date.now().toString(),
        name: data.name,
        description: data.description || '',
        version: data.version || "1.0.0",
        tags: data.tags ? data.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
        status: 'active',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        workspace_id: workspaceId!,
        config_schema: {
          workflow: {
            nodes: [],
            edges: []
          }
        }
      }
      
      setWorkflows(prev => [...prev, newWorkflow])
      setCreateDialogOpen(false)
      createForm.reset()
      toast.success('Workflow created successfully')
      
      // Redirect to workflow edit page
      router.push(`/dashboard/workflows/${newWorkflow.id}/edit`)
    } catch (error) {
      toast.error('Failed to create workflow')
    }
  }

  const handleDeleteWorkflow = async () => {
    if (!selectedWorkflow) return

    try {
      // Mock workflow deletion
      setWorkflows(prev => prev.filter(w => w.id !== selectedWorkflow.id))
      setDeleteDialogOpen(false)
      setSelectedWorkflow(null)
      toast.success('Workflow deleted successfully')
    } catch (error) {
      toast.error('Failed to delete workflow')
    }
  }

  const handleExecute = async (workflow: Workflow) => {
    setExecuting(workflow.id)
    try {
      // Mock workflow execution
      toast.success('Workflow executed successfully')
    } catch (error) {
      toast.error('Failed to execute workflow')
    } finally {
      setExecuting(null)
    }
  }

  const handleEdit = (workflow: Workflow) => {
    router.push(`/dashboard/workflows/${workflow.id}/edit`)
  }

  const handleDuplicate = async (workflow: Workflow) => {
    try {
      // Mock workflow duplication
      const duplicatedWorkflow: Workflow = {
        ...workflow,
        id: Date.now().toString(),
        name: `${workflow.name} (Copy)`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
      
      setWorkflows(prev => [...prev, duplicatedWorkflow])
      toast.success('Workflow duplicated successfully')
    } catch (error) {
      toast.error('Failed to duplicate workflow')
    }
  }

  const handleTemplateSelect = async (template: any) => {
    try {
      // Mock workflow creation from template
      const newWorkflow: Workflow = {
        id: Date.now().toString(),
        name: template.name,
        description: template.description,
        version: "1.0.0",
        tags: template.tags,
        status: 'active',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        workspace_id: workspaceId!,
        config_schema: {
          template: template.id,
          workflow: {
            nodes: [
              {
                id: "start",
                type: "trigger",
                position: { x: 250, y: 50 },
                data: { label: template.name, type: "trigger" },
              }
            ],
            edges: []
          }
        }
      }
      
      setWorkflows(prev => [...prev, newWorkflow])
      setTemplateDialogOpen(false)
      toast.success(`Workflow created from template: ${template.name}`)
      
      // Redirect to workflow edit page
      router.push(`/dashboard/workflows/${newWorkflow.id}/edit`)
    } catch (error) {
      toast.error('Failed to create workflow from template')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2">Loading workflows...</span>
      </div>
    )
  }

  if (!isReady) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2">Initializing workspace...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <WorkflowIcon className="h-8 w-8 text-muted-foreground" />
          <div>
            <h1 className="text-3xl font-bold">Workflows</h1>
            <p className="text-muted-foreground">Create and manage automated workflows</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Create from Template Button */}
          <Button 
            variant="outline" 
            onClick={() => setTemplateDialogOpen(true)}
          >
            <Plus className="mr-2 h-4 w-4" />
            Create from Template
          </Button>
          
          {/* Create Workflow Button */}
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Workflow
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-3xl">
              <DialogHeader>
                <DialogTitle>Create New Workflow</DialogTitle>
                <DialogDescription>
                  Add a new automated workflow to your workspace
                </DialogDescription>
              </DialogHeader>
              <Form {...createForm}>
                <form onSubmit={createForm.handleSubmit(handleCreateWorkflow)} className="space-y-4">
                  <FormField
                    control={createForm.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Workflow name" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={createForm.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Textarea placeholder="Workflow description" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={createForm.control}
                    name="version"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Version</FormLabel>
                        <FormControl>
                          <Input placeholder="1.0.0" {...field} />
                        </FormControl>
                        <FormDescription>
                          Semantic version (e.g., 1.0.0)
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={createForm.control}
                    name="tags"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Tags</FormLabel>
                        <FormControl>
                          <Input placeholder="automation, daily, data-sync" {...field} />
                        </FormControl>
                        <FormDescription>
                          Comma-separated tags
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <DialogFooter>
                    <Button 
                      type="button" 
                      variant="outline" 
                      onClick={() => {
                        setCreateDialogOpen(false)
                        createForm.reset()
                      }}
                    >
                      Cancel
                    </Button>
                    <Button type="submit">
                      Create Workflow
                    </Button>
                  </DialogFooter>
                </form>
              </Form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                {stat.change}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Workflows Table */}
      <Card>
        <CardHeader>
          <CardTitle>Workflows</CardTitle>
          <CardDescription>
            Manage your automated workflows and their execution status
          </CardDescription>
        </CardHeader>
        <CardContent>
          {workflows.length === 0 ? (
            <div className="text-center py-12">
              <WorkflowIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No workflows yet</h3>
              <p className="text-muted-foreground mb-4">
                Create your first workflow to automate tasks and processes
              </p>
              <div className="flex gap-2 justify-center">
                <Button onClick={() => setCreateDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Workflow
                </Button>
                <Button variant="outline" onClick={() => setTemplateDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  Use Template
                </Button>
              </div>
            </div>
          ) : (
            <DataTable
              columns={workflowColumns}
              data={workflows}
              toolbar={DataTableToolbar}
            />
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the workflow
              "{selectedWorkflow?.name}".
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteWorkflow}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Template Selection Dialog */}
      <CreateWorkflowTemplateDialog
        open={templateDialogOpen}
        onOpenChange={setTemplateDialogOpen}
        onTemplateSelect={handleTemplateSelect}
      />
    </div>
  )
}
