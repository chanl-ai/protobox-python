"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useWorkspaceReady } from "@/hooks"
import { useActions, useCreateAction, useDeleteAction, type Action } from "@/lib/api/hooks"
import { protoboxClient } from "@/lib/api/protobox-client"
import { ColumnDef } from "@tanstack/react-table"
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
  Play, 
  Trash2, 
  Edit, 
  LayoutGrid, 
  Table as TableIcon,
  Globe,
  Database,
  Code,
  Bot,
  MoreHorizontal,
  Plus,
  CheckCircle,
  Loader2,
  Download,
  ChevronDown
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
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

import { ReusableTable } from "@/components/reusable-table"
import { ImportActionsDialog } from "@/components/import-actions-dialog"

// Form validation schemas
const actionFormSchema = z.object({
  name: z.string()
    .min(1, "Action name is required")
    .max(255, "Action name must be less than 255 characters"),
  description: z.string()
    .min(1, "Description is required")
    .max(1000, "Description must be less than 1000 characters"),
  type: z.enum(["REST", "DATABASE", "CODE_RUN", "O3"], {
    required_error: "Please select an action type",
  }),
  version: z.string()
    .min(1, "Version is required")
    .regex(/^\d+\.\d+\.\d+$/, "Version must be in format x.y.z"),
  tags: z.string().optional(),
})

type ActionFormData = z.infer<typeof actionFormSchema>

export default function ActionsPage() {
  const router = useRouter()
  const { workspaceId, isReady } = useWorkspaceReady()
  const { data: actions, isLoading: loading, error, refetch } = useActions(workspaceId || undefined)
  const createAction = useCreateAction()
  const deleteAction = useDeleteAction()
  const [viewMode, setViewMode] = useState<"table" | "grid">("table")
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedAction, setSelectedAction] = useState<Action | null>(null)
  const [executing, setExecuting] = useState<string | null>(null)

  // Form management
  const createForm = useForm<ActionFormData>({
    resolver: zodResolver(actionFormSchema),
    defaultValues: {
      name: "",
      description: "",
      type: "REST" as const,
      version: "1.0.0",
      tags: "",
    },
  })

  const typeIcons = {
    REST: Globe,
    DATABASE: Database,
    CODE_RUN: Code,
    O3: Bot,
  }

  const typeColors = {
    REST: "text-blue-500",
    DATABASE: "text-green-500", 
    CODE_RUN: "text-orange-500",
    O3: "text-purple-500",
  }

  // Actions are loaded automatically by useActions hook
  // No manual loading needed

  // Define table columns
  const columns: ColumnDef<Action>[] = [
    {
      accessorKey: "name",
      header: "Name & Description",
      cell: ({ row }) => {
        const Icon = typeIcons[row.original.type as keyof typeof typeIcons] || Settings
        const colorClass = typeColors[row.original.type as keyof typeof typeColors] || "text-gray-500"
        return (
          <div className="flex items-start space-x-3 max-w-md">
            <div className="p-1.5 rounded-md bg-muted mt-0.5 flex-shrink-0">
              <Icon className={`h-4 w-4 ${colorClass}`} />
            </div>
            <div className="min-w-0 flex-1">
              <button 
                onClick={() => handleEdit(row.original)}
                className="font-medium text-left hover:text-primary hover:underline transition-colors block w-full text-left"
                data-testid={`action-name-${row.original.id}`}
              >
                {row.original.name}
              </button>
              <div className="text-sm text-muted-foreground mt-1 line-clamp-2">
                {row.original.description || "No description"}
              </div>
            </div>
          </div>
        )
      },
    },
    {
      accessorKey: "type",
      header: "Type",
      cell: ({ row }) => (
        <Badge variant="secondary">{row.original.type}</Badge>
      ),
    },
    {
      accessorKey: "status", 
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={row.original.status === "active" ? "default" : "destructive"}>
          {row.original.status === "active" ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      accessorKey: "created_at",
      header: "Created",
      cell: ({ row }) => (
        <div className="text-sm text-muted-foreground">
          {new Date(row.original.created_at).toLocaleDateString()}
        </div>
      ),
    },
    {
      id: "actions",
      header: "Actions",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => handleExecute(row.original)}>
              <Play className="mr-2 h-4 w-4" />
              Execute
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleValidate(row.original)}>
              <CheckCircle className="mr-2 h-4 w-4" />
              Validate
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleEdit(row.original)} data-testid={`edit-action-${row.original.id}`}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              onClick={() => handleDelete(row.original)}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ]

  const handleCreateAction = async (data: ActionFormData) => {
    try {
      await createAction.mutateAsync({
        name: data.name,
        description: data.description,
        type: data.type,
        version: data.version,
        default_config: {},
        config_schema: {},
        tags: data.tags ? data.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
      })
      setCreateDialogOpen(false)
      createForm.reset()
      toast.success('Action created successfully')
    } catch (error) {
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
    try {
      const response = await protoboxClient.validateAction(workspaceId || undefined, action.id)
      
      if (response.data) {
        toast.success('Action is valid')
      } else {
        toast.error(response.error || 'Action validation failed')
      }
    } catch (error) {
      toast.error('Failed to validate action')
    }
  }

  const handleEdit = (action: Action) => {
    router.push(`/workspace/${workspaceId}/dashboard/actions/${action.id}`)
  }

  const handleDelete = (action: Action) => {
    setSelectedAction(action)
    setDeleteDialogOpen(true)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  const stats = [
    { title: "Total Actions", value: (actions?.length || 0).toString(), change: `${(actions?.filter(a => a.status === 'active').length || 0)} active` },
    { title: "Active Actions", value: (actions?.filter(a => a.status === 'active').length || 0).toString(), change: `${(actions?.filter(a => a.status !== 'active').length || 0)} inactive` },
    { title: "Action Types", value: (actions ? new Set(actions.map(a => a.type)).size : 0).toString(), change: "Different types" },
    { title: "Success Rate", value: "98.2%", change: "Based on executions" },
  ]

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
          {/* View Mode Toggle */}
          <div className="flex items-center rounded-lg border p-1">
            <Button
              variant={viewMode === "table" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setViewMode("table")}
              className="h-7 px-2"
            >
              <TableIcon className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === "grid" ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setViewMode("grid")}
              className="h-7 px-2"
            >
              <LayoutGrid className="h-4 w-4" />
            </Button>
          </div>
          
          {/* Create/Import Actions */}
          <div className="flex items-center gap-2">
            <ImportActionsDialog 
              onImportComplete={(result) => {
                toast.success(`Imported ${result.summary.created} actions successfully`)
                // Refresh the actions list
                refetch()
              }}
            />
            
            <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="mr-2 h-4 w-4" />
                  Create Action
                </Button>
              </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Create New Action</DialogTitle>
                <DialogDescription>
                  Add a new action to your workspace
                </DialogDescription>
              </DialogHeader>
              <Form {...createForm}>
                <form onSubmit={createForm.handleSubmit(handleCreateAction)} className="space-y-4">
                  <FormField
                    control={createForm.control}
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
                    control={createForm.control}
                    name="type"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Type</FormLabel>
                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Select action type" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="REST">REST API</SelectItem>
                            <SelectItem value="DATABASE">Database</SelectItem>
                            <SelectItem value="CODE_RUN">Code Run</SelectItem>
                            <SelectItem value="O3">AI Assistant</SelectItem>
                          </SelectContent>
                        </Select>
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
                          <Textarea placeholder="Action description" {...field} />
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
                          <Input placeholder="api, external, production" {...field} />
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
                      Create Action
                    </Button>
                  </DialogFooter>
                </form>
              </Form>
            </DialogContent>
            </Dialog>
          </div>
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
            {viewMode === "table" 
              ? "Manage your MCP actions in table view" 
              : "Browse your MCP actions in grid view"
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          {viewMode === "table" ? (
            <ReusableTable
              columns={columns}
              data={actions || []}
              searchKey="name"
              searchPlaceholder="Search actions..."
              filterOptions={[
                {
                  key: "type",
                  label: "Type",
                  options: [
                    { value: "REST", label: "REST API" },
                    { value: "DATABASE", label: "Database" },
                    { value: "CODE_RUN", label: "Code Run" },
                    { value: "O3", label: "AI Assistant" },
                  ],
                },
                {
                  key: "status",
                  label: "Status",
                  options: [
                    { value: "active", label: "Active" },
                    { value: "inactive", label: "Inactive" },
                  ],
                },
              ]}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {(actions || []).map((action) => {
                const Icon = typeIcons[action.type as keyof typeof typeIcons] || Settings
                const colorClass = typeColors[action.type as keyof typeof typeColors] || "text-gray-500"
                const isExecuting = executing === action.id
                
                return (
                  <Card key={action.id} className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="p-2 rounded-md bg-muted">
                        <Icon className={`h-5 w-5 ${colorClass}`} />
                      </div>
                      <Badge variant={action.status === "active" ? "default" : "destructive"}>
                        {action.status}
                      </Badge>
                    </div>
                    <div className="space-y-2">
                      <button 
                        onClick={() => handleEdit(action)}
                        className="font-semibold text-left hover:text-primary hover:underline transition-colors"
                        data-testid={`action-name-${action.id}`}
                      >
                        {action.name}
                      </button>
                      <p className="text-sm text-muted-foreground">
                        {action.description || "No description"}
                      </p>
                      <Badge variant="secondary">{action.type}</Badge>
                    </div>
                    <div className="flex gap-2 mt-4">
                      <Button 
                        size="sm" 
                        onClick={() => handleExecute(action)}
                        disabled={isExecuting}
                        className="flex-1"
                      >
                        {isExecuting ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Play className="h-4 w-4" />
                        )}
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleEdit(action)} data-testid={`edit-action-${action.id}`}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleDelete(action)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </Card>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>


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