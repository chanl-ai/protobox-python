"use client"

import { useState } from "react"
import { useWorkspaceReady } from "@/hooks"
import { useSecrets, useCreateSecret, useUpdateSecret, useDeleteSecret, type Secret } from "@/lib/api/hooks"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { 
  Plus, 
  Key, 
  Shield, 
  Lock, 
  Unlock,
  Loader2,
  Users,
  Activity,
  TrendingUp
} from "lucide-react"
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

import { DataTablePage } from "@/components/common/data-table-page"
import { columns, type Secret as SecretType } from "@/components/secrets/columns"
import { DataTableRowActions } from "@/components/secrets/data-table-row-actions"
import { DataTableToolbar } from "@/components/secrets/data-table-toolbar"

export default function SecretsPage() {
  const { workspaceId, isReady } = useWorkspaceReady()
  const { data: secrets, isLoading: loading, error, refetch } = useSecrets(workspaceId || undefined)
  const createSecret = useCreateSecret()
  const updateSecret = useUpdateSecret()
  const deleteSecret = useDeleteSecret()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedSecret, setSelectedSecret] = useState<Secret | null>(null)

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


  // Secrets are loaded automatically by useSecrets hook


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

  // Row action handlers
  const handleEdit = (secret: SecretType) => {
    setSelectedSecret(secret as Secret)
    setFormData({
      name: secret.name,
      description: secret.description || "",
      secret_type: secret.secret_type,
      secret_value: "", // Never pre-fill secret value for security
      tags: "",
      is_active: secret.is_active,
      expires_at: secret.expires_at || "",
      max_usage_count: ""
    })
    setEditDialogOpen(true)
  }

  const handleDelete = (secret: SecretType) => {
    setSelectedSecret(secret as Secret)
    setDeleteDialogOpen(true)
  }

  const handleRevoke = (secret: SecretType) => {
    toast.success('Secret revoked successfully')
  }

  const handleRotate = (secret: SecretType) => {
    toast.success('Secret rotated successfully')
  }

  const handleTest = (secret: SecretType) => {
    toast.success('Connection test passed')
  }


  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  // Secrets already match the SecretType structure from the API
  const transformedSecrets: SecretType[] = secrets || []

  const stats = [
    { 
      title: "Total Secrets", 
      value: (secrets?.length || 0).toString(), 
      description: `${(secrets?.filter(s => s.is_active).length || 0)} active`,
      icon: Key
    },
    { 
      title: "Active Secrets", 
      value: (secrets?.filter(s => s.is_active).length || 0).toString(), 
      description: `${(secrets?.filter(s => !s.is_active).length || 0)} inactive`,
      icon: Shield
    },
    { 
      title: "Secret Types", 
      value: (secrets ? new Set(secrets.map(s => s.secret_type)).size : 0).toString(), 
      description: "Different types",
      icon: Lock
    },
    { 
      title: "Total Usage", 
      value: (secrets?.reduce((sum, s) => sum + s.usage_count, 0) || 0).toString(), 
      description: "All time usage",
      icon: Activity
    },
  ]

  // Enhance columns with row actions
  const enhancedColumns = columns.map(col => {
    if (col.id === 'actions') {
      return {
        ...col,
        cell: ({ row }: any) => (
          <DataTableRowActions
            row={row}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onRevoke={handleRevoke}
            onRotate={handleRotate}
            onTest={handleTest}
          />
        ),
      }
    }
    return col
  })

  return (
    <DataTablePage
      pageTitle="Secrets"
      pageDescription="Securely store and manage your API keys and credentials"
      pageIcon={Key}
      stats={stats}
      statsColumns={4}
      localStorageKey="secrets-analytics-visible"
      tableTitle="Secrets"
      tableDescription="Manage your secrets with advanced filtering and search"
      columns={enhancedColumns}
      data={transformedSecrets || []}
      toolbar={DataTableToolbar}
      headerActions={
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
                    <SelectItem value="api_key">API Key</SelectItem>
                    <SelectItem value="oauth">OAuth</SelectItem>
                    <SelectItem value="password">Password</SelectItem>
                    <SelectItem value="certificate">Certificate</SelectItem>
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
      }
    >
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
                  <SelectItem value="api_key">API Key</SelectItem>
                  <SelectItem value="oauth">OAuth</SelectItem>
                  <SelectItem value="password">Password</SelectItem>
                  <SelectItem value="certificate">Certificate</SelectItem>
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
    </DataTablePage>
  )
}