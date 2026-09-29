"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useWorkspaceReady } from "@/hooks"
import { useActions, useCreateAction, useDeleteAction, type Action } from "@/lib/api/hooks"
import { protoboxClient } from "@/lib/api/protobox-client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { toast } from "sonner"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { 
  Settings, 
  Plus,
  Loader2,
  Download
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
import { columns as actionColumns } from "@/components/actions/columns"
import { DataTableRowActions } from "@/components/actions/data-table-row-actions"
import { DataTableToolbar } from "@/components/actions/data-table-toolbar"
import { Info } from "lucide-react"
import { ImportActionsDialog } from "@/components/import-actions-dialog"

// Action form schema
const actionFormSchema = z.object({
  name: z.string().min(1, "Name is required"),
  type: z.enum(["REST", "DATABASE", "CODE_RUN", "O3", "WORKFLOW"]).default("REST"),
  description: z.string().optional(),
  version: z.string().default("1.0.0"),
  tags: z.string().optional(),
  // REST specific fields
  url: z.string().optional(),
  method: z.enum(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]).optional(),
  // CODE_RUN specific fields
  language: z.enum(["python", "javascript"]).optional(),
  entry_point: z.string().optional(),
  timeout: z.number().optional(),
  memory_limit_mb: z.number().optional(),
  allow_network: z.boolean().optional(),
  allow_file_ops: z.boolean().optional(),
}).superRefine((data, ctx) => {
  // Make URL and method required for REST actions only
  if (data.type === "REST") {
    if (!data.url) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "URL is required for REST actions",
        path: ["url"],
      });
    } else if (data.url && !z.string().url().safeParse(data.url).success) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Must be a valid URL",
        path: ["url"],
      });
    }
    
    if (!data.method) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Method is required for REST actions",
        path: ["method"],
      });
    }
  }
})

type ActionFormData = z.infer<typeof actionFormSchema>

// Create a wrapper component for the toolbar with admin filter
function createDataTableToolbarWithAdminFilter(
  showAdminActions: boolean,
  onShowAdminActionsChange: (value: boolean) => void
) {
  return function ToolbarWithAdminFilter({ table }: { table: any }) {
    return (
      <DataTableToolbar
        table={table}
        showAdminActions={showAdminActions}
        onShowAdminActionsChange={onShowAdminActionsChange}
      />
    )
  }
}

export default function ActionsPage() {
  const router = useRouter()
  const { workspaceId, isReady } = useWorkspaceReady()
  const { data: actions, isLoading: loading, error, refetch } = useActions(workspaceId || undefined)
  const createAction = useCreateAction()
  const deleteAction = useDeleteAction()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedAction, setSelectedAction] = useState<Action | null>(null)
  const [executing, setExecuting] = useState<string | null>(null)
  const [showAdminActions, setShowAdminActions] = useState(false)
  const [adminInfoDialogOpen, setAdminInfoDialogOpen] = useState(false)
  const [selectedAdminAction, setSelectedAdminAction] = useState<Action | null>(null)

  // Create form
  const createForm = useForm<ActionFormData>({
    resolver: zodResolver(actionFormSchema) as any,
    defaultValues: {
      name: "",
      type: "REST" as const,
      description: "",
      version: "1.0.0",
      tags: "",
      url: "",
      method: "GET" as const,
      language: "javascript",
    },
  })

  // Watch for action type changes and clear fields when switching types
  const watchedType = createForm.watch("type")
  useEffect(() => {
    if (watchedType !== "REST") {
      // Clear REST-specific fields when switching away from REST
      createForm.setValue("url", "")
      createForm.setValue("method", "GET")
      // Clear any validation errors for these fields
      createForm.clearErrors(["url", "method"])
    }
    if (watchedType !== "CODE_RUN") {
      // Clear CODE_RUN-specific fields when switching away from CODE_RUN
      createForm.setValue("language", "javascript")
      createForm.setValue("entry_point", "")
      createForm.setValue("timeout", undefined)
      createForm.setValue("memory_limit_mb", undefined)
      createForm.setValue("allow_network", undefined)
      createForm.setValue("allow_file_ops", undefined)
    }
  }, [watchedType, createForm])

  // Listen for admin action clicks
  useEffect(() => {
    const handleAdminActionClick = (event: any) => {
      const action = event.detail
      setSelectedAdminAction(action)
      setAdminInfoDialogOpen(true)
    }

    document.addEventListener('admin-action-click', handleAdminActionClick)
    return () => {
      document.removeEventListener('admin-action-click', handleAdminActionClick)
    }
  }, [])

  // Calculate stats
  const stats = [
    {
      title: "Total Actions",
      value: (actions?.length || 0).toString(),
      change: "+2 from last month",
    },
    {
      title: "Active Actions",
      value: (actions?.filter(a => a.status === "active").length || 0).toString(),
      change: "+1 from last month",
    },
    {
      title: "Action Types",
      value: (actions ? [...new Set(actions.map(a => a.type))].length : 0).toString(),
      change: "No change",
    },
    {
      title: "Recent Executions",
      value: "0",
      change: "View all",
    },
  ]

  const handleCreateAction = async (data: ActionFormData) => {
    try {
      let actionData: any

      if (data.type === 'CODE_RUN') {
        // Create CODE_RUN action using ProtoboxClient
        const response = await protoboxClient.createCodeRunAction(workspaceId || undefined, {
          name: data.name,
          description: data.description || '',
          language: data.language || 'javascript',
          timeout: data.timeout,
          memory_limit_mb: data.memory_limit_mb,
          allow_network: data.allow_network,
          allow_file_ops: data.allow_file_ops,
          tags: data.tags || '',
        })
        if (response.error) throw new Error(response.error)
        actionData = response.data
      } else {
        // Create regular action using hook
        const defaultConfig: any = {}
        
        // Add URL and method for REST actions
        if (data.type === 'REST') {
          defaultConfig.url = data.url
          defaultConfig.method = data.method
          defaultConfig.headers = {}
        }
        
        actionData = await createAction.mutateAsync({
          name: data.name,
          description: data.description,
          type: data.type,
          version: data.version || "1.0.0",
          default_config: defaultConfig,
          config_schema: {},
          tags: data.tags ? data.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
        })
      }

      if (actionData) {
        setCreateDialogOpen(false)
        createForm.reset({
          name: "",
          type: "REST" as const,
          description: "",
          version: "1.0.0",
          tags: "",
          url: "",
          method: "GET" as const,
          language: "javascript",
        })
        toast.success('Action created successfully')
        
        // Redirect to the action page
        router.push(`/dashboard/actions/${actionData.id}`)
      }
    } catch (error) {
      console.error('Error creating action:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to create action')
    }
  }

  const handleDeleteAction = async () => {
    if (!selectedAction) return

    try {
      await deleteAction.mutateAsync(selectedAction.id)
      setDeleteDialogOpen(false)
      setSelectedAction(null)
      toast.success('Action deleted successfully')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete action')
    }
  }

  const handleExecute = async (action: Action) => {
    // Prevent execution through UI for admin actions
    if (!action.id || action.type === 'ADMIN') {
      toast.info('Admin actions are executed automatically by the system')
      return
    }
    setExecuting(action.id)
    try {
      const response = await protoboxClient.executeAction(workspaceId || undefined, action.id)
      
      if (response.data) {
        toast.success('Action executed successfully')
      } else {
        toast.error(response.error || 'Failed to execute action')
      }
    } catch (error) {
      toast.error('Failed to execute action')
    } finally {
      setExecuting(null)
    }
  }

  const handleValidate = async (action: Action) => {
    // Admin actions are always valid
    if (!action.id || action.type === 'ADMIN') {
      toast.info('Admin actions are pre-validated system tools')
      return
    }
    try {
      const response = await protoboxClient.validateAction(workspaceId || undefined, action.id)
      
      if (response.data) {
        toast.success('Action validated successfully')
      } else {
        toast.error(response.error || 'Failed to validate action')
      }
    } catch (error) {
      toast.error('Failed to validate action')
    }
  }

  const handleEdit = (action: Action) => {
    // Check if this is an admin action (null ID or type ADMIN)
    if (!action.id || action.id === 'null' || action.id === 'undefined' || action.type === 'ADMIN') {
      setSelectedAdminAction(action)
      setAdminInfoDialogOpen(true)
      return
    }
    router.push(`/dashboard/actions/${action.id}`)
  }

  const handleDelete = (action: Action) => {
    // Prevent deletion of admin actions
    if (!action.id || action.type === 'ADMIN') {
      toast.error('Admin actions cannot be deleted')
      return
    }
    setSelectedAction(action)
    setDeleteDialogOpen(true)
  }

  const handleDuplicate = async (action: Action) => {
    // Prevent duplication of admin actions
    if (!action.id || action.type === 'ADMIN') {
      toast.error('Admin actions cannot be duplicated')
      return
    }
    try {
      const { id, created_at, updated_at, created_by, workspace_id, ...actionData } = action
      const duplicated = await createAction.mutateAsync({
        ...actionData,
        name: `${action.name} (Copy)`,
      })
      toast.success('Action duplicated successfully')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to duplicate action')
    }
  }

  // Enhance columns with row actions
  const enhancedColumns = actionColumns.map(col => {
    if (col.id === 'actions') {
      return {
        ...col,
        cell: ({ row }: any) => (
          <DataTableRowActions
            row={row}
            onExecute={handleExecute}
            onValidate={handleValidate}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onDuplicate={handleDuplicate}
          />
        ),
      }
    }
    return col
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2">Loading actions...</span>
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
          <Settings className="h-8 w-8 text-muted-foreground" />
          <div>
            <h1 className="text-3xl font-bold">Actions</h1>
            <p className="text-muted-foreground">Create and manage your MCP actions</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Import Actions Button */}
          <ImportActionsDialog 
            onImportComplete={(result) => {
              toast.success(`Imported ${result.summary.created} actions successfully`)
              // Refresh the actions list
              refetch()
            }}
          />
          
          {/* Create Action Button */}
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Action
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-3xl">
              <DialogHeader>
                <DialogTitle>Create New Action</DialogTitle>
                <DialogDescription>
                  Add a new action to your workspace
                </DialogDescription>
              </DialogHeader>
              <Form {...createForm}>
                <form onSubmit={createForm.handleSubmit(handleCreateAction)} className="space-y-4">
                  <FormField
                    control={createForm.control as any}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Name</FormLabel>
                        <FormControl>
                          <Input placeholder="Action name" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={createForm.control as any}
                    name="type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Type</FormLabel>
                        <FormControl>
                          <ActionTypeSelector
                            value={field.value}
                            onChange={field.onChange}
                            columns={2}
                            required
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={createForm.control as any}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Textarea placeholder="Action description" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={createForm.control as any}
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
                    control={createForm.control as any}
                    name="tags"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Tags</FormLabel>
                        <FormControl>
                          <Input placeholder="api, external, production" {...field} />
                        </FormControl>
                        <FormDescription>
                          Comma-separated tags
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {/* REST specific fields - only show when type is REST */}
                  {createForm.watch("type") === "REST" && (
                    <>
                      <FormField
                        control={createForm.control as any}
                        name="url"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>URL *</FormLabel>
                            <FormControl>
                              <Input placeholder="https://api.example.com/endpoint" {...field} />
                            </FormControl>
                            <FormDescription>
                              The API endpoint URL
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      
                      <FormField
                        control={createForm.control as any}
                        name="method"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Method *</FormLabel>
                            <FormControl>
                              <Select value={field.value} onValueChange={field.onChange}>
                                <SelectTrigger>
                                  <SelectValue placeholder="Select HTTP method" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="GET">GET</SelectItem>
                                  <SelectItem value="POST">POST</SelectItem>
                                  <SelectItem value="PUT">PUT</SelectItem>
                                  <SelectItem value="DELETE">DELETE</SelectItem>
                                  <SelectItem value="PATCH">PATCH</SelectItem>
                                  <SelectItem value="HEAD">HEAD</SelectItem>
                                  <SelectItem value="OPTIONS">OPTIONS</SelectItem>
                                </SelectContent>
                              </Select>
                            </FormControl>
                            <FormDescription>
                              HTTP method for the request
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </>
                  )}

                  {/* CODE_RUN specific fields - only show when type is CODE_RUN */}
                  {createForm.watch("type") === "CODE_RUN" && (
                    <>
                      <FormField
                        control={createForm.control as any}
                        name="language"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Language</FormLabel>
                            <FormControl>
                              <Select value={field.value} onValueChange={field.onChange}>
                                <SelectTrigger>
                                  <SelectValue placeholder="Select language" />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="javascript">JavaScript</SelectItem>
                                  <SelectItem value="python">Python</SelectItem>
                                </SelectContent>
                              </Select>
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </>
                  )}
                  
                  <DialogFooter>
                    <Button 
                      type="button" 
                      variant="outline" 
                      onClick={() => {
                        setCreateDialogOpen(false)
                        createForm.reset({
                          name: "",
                          type: "REST" as const,
                          description: "",
                          version: "1.0.0",
                          tags: "",
                          url: "",
                          method: "GET" as const,
                          language: "javascript",
                        })
                      }}
                    >
                      Cancel
                    </Button>
                    <Button type="submit">
                      Create Action
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
        {stats.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">{stat.change}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Actions Content */}
      <Card>
        <CardHeader>
          <CardTitle>Actions</CardTitle>
          <CardDescription>
            Manage your MCP actions with advanced filtering and search
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={enhancedColumns}
            data={showAdminActions ? (actions || []) : (actions || []).filter(a => a.type !== 'ADMIN' && a.id)}
            toolbar={createDataTableToolbarWithAdminFilter(showAdminActions, setShowAdminActions)}
          />
        </CardContent>
      </Card>

      {/* Admin Action Info Dialog */}
      <Dialog open={adminInfoDialogOpen} onOpenChange={setAdminInfoDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Info className="h-5 w-5" />
              Admin Action: {selectedAdminAction?.name}
            </DialogTitle>
            <DialogDescription>
              This is a system-provided administrative action
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <h4 className="font-medium mb-2">About Admin Actions</h4>
              <p className="text-sm text-muted-foreground">
                Admin actions are built-in MCP tools that help manage your workspace.
                They are automatically available and cannot be modified or deleted.
              </p>
            </div>
            {selectedAdminAction?.description && (
              <div>
                <h4 className="font-medium mb-2">Description</h4>
                <p className="text-sm text-muted-foreground">
                  {selectedAdminAction.description}
                </p>
              </div>
            )}
            <div>
              <h4 className="font-medium mb-2">Usage</h4>
              <p className="text-sm text-muted-foreground">
                Admin actions are called automatically by AI assistants when needed.
                They handle workspace management tasks like creating actions, managing secrets,
                and configuring integrations.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setAdminInfoDialogOpen(false)}>
              Got it
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the action
              &quot;{selectedAction?.name}&quot; and remove all associated data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteAction}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}