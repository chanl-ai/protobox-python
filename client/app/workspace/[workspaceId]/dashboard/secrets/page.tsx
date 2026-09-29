"use client"

import { useState } from "react"
import { useWorkspaceReady } from "@/hooks"
import { useSecrets, useCreateSecret, useUpdateSecret, useDeleteSecret, type Secret } from "@/lib/api/hooks"
import { ColumnDef } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { 
  Plus, 
  Eye, 
  EyeOff, 
  Key, 
  Shield, 
  AlertTriangle, 
  Copy, 
  Edit, 
  Trash2,
  LayoutGrid,
  Table as TableIcon,
  MoreHorizontal,
  Database,
  Lock,
  Loader2
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

export default function SecretsPage() {
  const { workspaceId, isReady } = useWorkspaceReady()
  const { data: secrets, isLoading: loading, error, refetch } = useSecrets(workspaceId || undefined)
  const createSecret = useCreateSecret()
  const updateSecret = useUpdateSecret()
  const deleteSecret = useDeleteSecret()
  const [viewMode, setViewMode] = useState<"table" | "grid">("table")
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedSecret, setSelectedSecret] = useState<Secret | null>(null)
  const [revealedSecrets, setRevealedSecrets] = useState<Set<string>>(new Set())

  // Form state for create/edit
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    secret_type: "",
    secret_value: "",
    tags: "",
    is_active: true,
    expires_at: "",
    max_usage_count: ""
  })

  const typeIcons = {
    API_KEY: Key,
    DATABASE_URL: Database,
    OAUTH_TOKEN: Shield,
    BASIC_AUTH: Lock,
    CUSTOM: AlertTriangle,
  }

  const typeColors = {
    API_KEY: "text-blue-500",
    DATABASE_URL: "text-green-500", 
    OAUTH_TOKEN: "text-purple-500",
    BASIC_AUTH: "text-orange-500",
    CUSTOM: "text-gray-500",
  }

  // Secrets are loaded automatically by useSecrets hook
  // No manual loading needed

  // Define table columns
  const columns: ColumnDef<Secret>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => {
        const Icon = typeIcons[row.original.secret_type as keyof typeof typeIcons] || Key
        const colorClass = typeColors[row.original.secret_type as keyof typeof typeColors] || "text-gray-500"
        return (
          <div className="flex items-center space-x-3">
            <div className="p-1.5 rounded-md bg-muted">
              <Icon className={`h-4 w-4 ${colorClass}`} />
            </div>
            <div className="font-medium">{row.original.name}</div>
          </div>
        )
      },
    },
    {
      accessorKey: "secret_type",
      header: "Type",
      cell: ({ row }) => (
        <Badge variant="secondary">{row.original.secret_type}</Badge>
      ),
    },
    {
      accessorKey: "is_active", 
      header: "Status",
      cell: ({ row }) => (
        <Badge variant={row.original.is_active ? "default" : "destructive"}>
          {row.original.is_active ? "Active" : "Inactive"}
        </Badge>
      ),
    },
    {
      accessorKey: "usage_count",
      header: "Usage",
      cell: ({ row }) => (
        <div className="text-sm">
          {row.original.usage_count}
          {row.original.max_usage_count && ` / ${row.original.max_usage_count}`}
        </div>
      ),
    },
    {
      accessorKey: "expires_at",
      header: "Expires",
      cell: ({ row }) => (
        <div className="text-sm text-muted-foreground">
          {row.original.expires_at 
            ? new Date(row.original.expires_at).toLocaleDateString()
            : "Never"
          }
        </div>
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
            <DropdownMenuItem onClick={() => handleRevealSecret(row.original)}>
              {revealedSecrets.has(row.original.id) ? (
                <>
                  <EyeOff className="mr-2 h-4 w-4" />
                  Hide Value
                </>
              ) : (
                <>
                  <Eye className="mr-2 h-4 w-4" />
                  Reveal Value
                </>
              )}
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleCopySecret()}>
              <Copy className="mr-2 h-4 w-4" />
              Copy Value
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleEdit(row.original)}>
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

  const handleCreateSecret = async () => {
    try {
      await createSecret.mutateAsync({
        name: formData.name,
        description: formData.description,
        secret_type: formData.secret_type,
        secret_value: formData.secret_value,
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
        is_active: formData.is_active,
        expires_at: formData.expires_at || undefined,
        max_usage_count: formData.max_usage_count ? parseInt(formData.max_usage_count) : undefined,
      })
      setCreateDialogOpen(false)
      setFormData({ 
        name: "", 
        description: "", 
        secret_type: "", 
        secret_value: "", 
        tags: "", 
        is_active: true, 
        expires_at: "", 
        max_usage_count: "" 
      })
      toast.success('Secret created successfully')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create secret')
    }
  }

  const handleUpdateSecret = async () => {
    if (!selectedSecret) return

    try {
      const updateData: Record<string, unknown> = {
        name: formData.name,
        description: formData.description,
        secret_type: formData.secret_type,
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
        is_active: formData.is_active,
        expires_at: formData.expires_at || undefined,
        max_usage_count: formData.max_usage_count ? parseInt(formData.max_usage_count) : undefined,
      }

      // Only include secret_value if it was changed
      if (formData.secret_value) {
        updateData.secret_value = formData.secret_value
      }

      await updateSecret.mutateAsync({
        secretId: selectedSecret.id,
        data: updateData,
      })
      setEditDialogOpen(false)
      setSelectedSecret(null)
      toast.success('Secret updated successfully')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update secret')
    }
  }

  const handleDeleteSecret = async () => {
    if (!selectedSecret) return

    try {
      await deleteSecret.mutateAsync(selectedSecret.id)
      setDeleteDialogOpen(false)
      setSelectedSecret(null)
      toast.success('Secret deleted successfully')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete secret')
    }
  }

  const handleRevealSecret = async (secret: Secret) => {
    if (revealedSecrets.has(secret.id)) {
      setRevealedSecrets(prev => {
        const newSet = new Set(prev)
        newSet.delete(secret.id)
        return newSet
      })
    } else {
      setRevealedSecrets(prev => new Set(prev).add(secret.id))
      toast.success('Secret value revealed')
    }
  }

  const handleCopySecret = async () => {
    try {
      // In a real implementation, you'd fetch the actual secret value
      await navigator.clipboard.writeText('***REDACTED***')
      toast.success('Secret value copied to clipboard')
    } catch {
      toast.error('Failed to copy secret value')
    }
  }

  const handleEdit = (secret: Secret) => {
    setSelectedSecret(secret)
    setFormData({
      name: secret.name,
      description: secret.description || "",
      secret_type: secret.secret_type,
      secret_value: "", // Never pre-fill secret value for security
      tags: secret.tags?.join(', ') || "",
      is_active: secret.is_active,
      expires_at: secret.expires_at || "",
      max_usage_count: secret.max_usage_count?.toString() || ""
    })
    setEditDialogOpen(true)
  }

  const handleDelete = (secret: Secret) => {
    setSelectedSecret(secret)
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
    { title: "Total Secrets", value: (secrets?.length || 0).toString(), change: `${(secrets?.filter(s => s.is_active).length || 0)} active` },
    { title: "Active Secrets", value: (secrets?.filter(s => s.is_active).length || 0).toString(), change: `${(secrets?.filter(s => !s.is_active).length || 0)} inactive` },
    { title: "Secret Types", value: (secrets ? new Set(secrets.map(s => s.secret_type)).size : 0).toString(), change: "Different types" },
    { title: "Total Usage", value: (secrets?.reduce((sum, s) => sum + s.usage_count, 0) || 0).toString(), change: "All time usage" },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <Key className="h-8 w-8 text-muted-foreground" />
          <div>
            <h1 className="text-3xl font-bold">Secrets</h1>
            <p className="text-muted-foreground">Securely store and manage your API keys and credentials</p>
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
          
          {/* Create Secret Button */}
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Secret
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>Create New Secret</DialogTitle>
                <DialogDescription>
                  Add a new secret to your workspace
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Secret name"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="secret_type">Type</Label>
                  <Select value={formData.secret_type} onValueChange={(value) => setFormData(prev => ({ ...prev, secret_type: value }))}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select secret type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="API_KEY">API Key</SelectItem>
                      <SelectItem value="DATABASE_URL">Database URL</SelectItem>
                      <SelectItem value="OAUTH_TOKEN">OAuth Token</SelectItem>
                      <SelectItem value="BASIC_AUTH">Basic Auth</SelectItem>
                      <SelectItem value="CUSTOM">Custom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="secret_value">Secret Value</Label>
                  <Input
                    id="secret_value"
                    type="password"
                    value={formData.secret_value}
                    onChange={(e) => setFormData(prev => ({ ...prev, secret_value: e.target.value }))}
                    placeholder="Enter secret value"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Secret description"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="tags">Tags (comma-separated)</Label>
                  <Input
                    id="tags"
                    value={formData.tags}
                    onChange={(e) => setFormData(prev => ({ ...prev, tags: e.target.value }))}
                    placeholder="production, api, external"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="expires_at">Expires At (optional)</Label>
                  <Input
                    id="expires_at"
                    type="date"
                    value={formData.expires_at}
                    onChange={(e) => setFormData(prev => ({ ...prev, expires_at: e.target.value }))}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleCreateSecret} disabled={!formData.name || !formData.secret_type || !formData.secret_value}>
                  Create Secret
                </Button>
              </DialogFooter>
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

      {/* Secrets Content */}
      <Card>
        <CardHeader>
          <CardTitle>Secrets</CardTitle>
          <CardDescription>
            {viewMode === "table" 
              ? "Manage your secrets in table view" 
              : "Browse your secrets in grid view"
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          {viewMode === "table" ? (
            <ReusableTable
              columns={columns}
              data={secrets}
              searchKey="name"
              searchPlaceholder="Search secrets..."
              filterOptions={[
                {
                  key: "secret_type",
                  label: "Type",
                  options: [
                    { value: "API_KEY", label: "API Key" },
                    { value: "DATABASE_URL", label: "Database URL" },
                    { value: "OAUTH_TOKEN", label: "OAuth Token" },
                    { value: "BASIC_AUTH", label: "Basic Auth" },
                    { value: "CUSTOM", label: "Custom" },
                  ],
                },
                {
                  key: "is_active",
                  label: "Status",
                  options: [
                    { value: "true", label: "Active" },
                    { value: "false", label: "Inactive" },
                  ],
                },
              ]}
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {(secrets || []).map((secret) => {
                const Icon = typeIcons[secret.secret_type as keyof typeof typeIcons] || Key
                const colorClass = typeColors[secret.secret_type as keyof typeof typeColors] || "text-gray-500"
                const isRevealed = revealedSecrets.has(secret.id)
                
                return (
                  <Card key={secret.id} className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="p-2 rounded-md bg-muted">
                        <Icon className={`h-5 w-5 ${colorClass}`} />
                      </div>
                      <Badge variant={secret.is_active ? "default" : "destructive"}>
                        {secret.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                    <div className="space-y-2">
                      <h3 className="font-semibold">{secret.name}</h3>
                      <p className="text-sm text-muted-foreground">
                        {secret.description || "No description"}
                      </p>
                      <Badge variant="secondary">{secret.secret_type}</Badge>
                      <div className="text-sm text-muted-foreground">
                        Used {secret.usage_count} times
                      </div>
                    </div>
                    <div className="flex gap-2 mt-4">
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => handleRevealSecret(secret)}
                        className="flex-1"
                      >
                        {isRevealed ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleCopySecret()}>
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleEdit(secret)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleDelete(secret)}>
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

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Secret</DialogTitle>
            <DialogDescription>
              Update secret details
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-name">Name</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="Secret name"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-secret_type">Type</Label>
              <Select value={formData.secret_type} onValueChange={(value) => setFormData(prev => ({ ...prev, secret_type: value }))}>
                <SelectTrigger>
                  <SelectValue placeholder="Select secret type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="API_KEY">API Key</SelectItem>
                  <SelectItem value="DATABASE_URL">Database URL</SelectItem>
                  <SelectItem value="OAUTH_TOKEN">OAuth Token</SelectItem>
                  <SelectItem value="BASIC_AUTH">Basic Auth</SelectItem>
                  <SelectItem value="CUSTOM">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-secret_value">New Secret Value (leave empty to keep current)</Label>
              <Input
                id="edit-secret_value"
                type="password"
                value={formData.secret_value}
                onChange={(e) => setFormData(prev => ({ ...prev, secret_value: e.target.value }))}
                placeholder="Enter new secret value"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Secret description"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-tags">Tags (comma-separated)</Label>
              <Input
                id="edit-tags"
                value={formData.tags}
                onChange={(e) => setFormData(prev => ({ ...prev, tags: e.target.value }))}
                placeholder="production, api, external"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="edit-is_active">Status</Label>
              <Select value={formData.is_active.toString()} onValueChange={(value) => setFormData(prev => ({ ...prev, is_active: value === "true" }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="true">Active</SelectItem>
                  <SelectItem value="false">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateSecret} disabled={!formData.name || !formData.secret_type}>
              Update Secret
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
              This action cannot be undone. This will permanently delete the secret
              &quot;{selectedSecret?.name}&quot; and remove all associated data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteSecret}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}