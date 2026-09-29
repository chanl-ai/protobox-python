"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useToast } from "@/components/ui/toast-notification"
import { 
  Key,
  Plus,
  Copy,
  Eye,
  EyeOff,
  MoreHorizontal,
  Trash2,
  RotateCcw,
  Shield,
  Clock
} from "lucide-react"

// Dummy API keys
const mockApiKeys = [
  {
    id: "key_1",
    name: "Production API Key",
    key: "pk_live_EXAMPLE",
    keyPreview: "pk_live_EXA...PLE",
    permissions: ["read", "write"],
    lastUsed: "2 hours ago",
    created: "2024-01-15",
    status: "active"
  },
  {
    id: "key_2",
    name: "Development API Key", 
    key: "pk_test_EXAMPLE",
    keyPreview: "pk_test_EXA...PLE",
    permissions: ["read"],
    lastUsed: "1 day ago",
    created: "2024-02-10",
    status: "active"
  },
  {
    id: "key_3",
    name: "Staging Environment",
    key: "pk_staging_def456ghi789jkl012mno345pqr678stu901vwx234yza",
    keyPreview: "pk_staging_def456...4yza",
    permissions: ["read", "write", "admin"],
    lastUsed: "Never",
    created: "2024-07-15",
    status: "inactive"
  }
]

interface ApiKeysPageProps {
  params: { partnerId: string }
}

export default function ApiKeysPage({ params }: ApiKeysPageProps) {
  const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set())
  const [newKeyName, setNewKeyName] = useState("")
  const { toast, ToastContainer } = useToast()

  const toggleKeyVisibility = (keyId: string) => {
    const newVisible = new Set(visibleKeys)
    if (newVisible.has(keyId)) {
      newVisible.delete(keyId)
    } else {
      newVisible.add(keyId)
    }
    setVisibleKeys(newVisible)
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast("API key copied to clipboard", "success")
    } catch (error) {
      toast("Failed to copy API key", "error")
    }
  }

  const createApiKey = () => {
    if (!newKeyName.trim()) {
      toast("Please enter a name for the API key", "error")
      return
    }
    
    // Simulate API key creation
    toast("API key created successfully", "success")
    setNewKeyName("")
  }

  const regenerateKey = (keyId: string) => {
    toast("API key regenerated successfully", "success")
  }

  const deleteKey = (keyId: string) => {
    toast("API key deleted successfully", "success")
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-green-100 text-green-800">Active</Badge>
      case "inactive":
        return <Badge className="bg-gray-100 text-gray-800">Inactive</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const getPermissionsBadge = (permissions: string[]) => {
    return permissions.map((permission) => (
      <Badge key={permission} variant="outline" className="mr-1">
        {permission}
      </Badge>
    ))
  }

  return (
    <div className="space-y-6">
      {/* API Keys Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            API Keys
          </CardTitle>
          <CardDescription>
            Manage your partner API keys for authentication and access control
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label className="text-sm font-medium text-muted-foreground">Total Keys</Label>
              <p className="text-2xl font-bold">{mockApiKeys.length}</p>
            </div>
            <div>
              <Label className="text-sm font-medium text-muted-foreground">Active Keys</Label>
              <p className="text-2xl font-bold">
                {mockApiKeys.filter(k => k.status === "active").length}
              </p>
            </div>
            <div>
              <Label className="text-sm font-medium text-muted-foreground">Last Used</Label>
              <p className="text-sm">2 hours ago</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Create New API Key */}
      <Card>
        <CardHeader>
          <CardTitle>Create New API Key</CardTitle>
          <CardDescription>
            Generate a new API key for your partner integrations
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-end space-x-4">
            <div className="flex-1">
              <Label htmlFor="keyName">API Key Name</Label>
              <Input
                id="keyName"
                placeholder="e.g. Production API Key"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
              />
            </div>
            <Dialog>
              <DialogTrigger asChild>
                <Button disabled={!newKeyName.trim()}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Key
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create API Key</DialogTitle>
                  <DialogDescription>
                    This will create a new API key with read and write permissions.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label>API Key Name</Label>
                    <Input value={newKeyName} disabled />
                  </div>
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="flex items-start space-x-2">
                      <Shield className="h-5 w-5 text-yellow-600 mt-0.5" />
                      <div>
                        <p className="font-medium text-yellow-800">Security Notice</p>
                        <p className="text-sm text-yellow-700">
                          Make sure to copy and store this API key securely. You won't be able to see it again.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setNewKeyName("")}>
                    Cancel
                  </Button>
                  <Button onClick={createApiKey}>
                    Create API Key
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>

      {/* API Keys Table */}
      <Card>
        <CardHeader>
          <CardTitle>Your API Keys</CardTitle>
          <CardDescription>
            Manage existing API keys and their permissions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>API Key</TableHead>
                <TableHead>Permissions</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Used</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockApiKeys.map((apiKey) => (
                <TableRow key={apiKey.id}>
                  <TableCell>
                    <div>
                      <div className="font-medium">{apiKey.name}</div>
                      <div className="text-sm text-muted-foreground">
                        Created {new Date(apiKey.created).toLocaleDateString()}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <code className="font-mono text-sm">
                        {visibleKeys.has(apiKey.id) ? apiKey.key : apiKey.keyPreview}
                      </code>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleKeyVisibility(apiKey.id)}
                      >
                        {visibleKeys.has(apiKey.id) ? (
                          <EyeOff className="h-4 w-4" />
                        ) : (
                          <Eye className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(apiKey.key)}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell>
                    {getPermissionsBadge(apiKey.permissions)}
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(apiKey.status)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    <div className="flex items-center space-x-1">
                      <Clock className="h-3 w-3" />
                      <span>{apiKey.lastUsed}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => regenerateKey(apiKey.id)}>
                          <RotateCcw className="mr-2 h-4 w-4" />
                          Regenerate
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => copyToClipboard(apiKey.key)}>
                          <Copy className="mr-2 h-4 w-4" />
                          Copy Key
                        </DropdownMenuItem>
                        <Separator />
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                              <Trash2 className="mr-2 h-4 w-4 text-red-500" />
                              <span className="text-red-600">Delete</span>
                            </DropdownMenuItem>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete API Key</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete "{apiKey.name}"? This action cannot be undone
                                and will immediately revoke access for any applications using this key.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                className="bg-red-600 hover:bg-red-700"
                                onClick={() => deleteKey(apiKey.id)}
                              >
                                Delete Key
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* API Usage Guidelines */}
      <Card>
        <CardHeader>
          <CardTitle>API Usage Guidelines</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2">Authentication</h4>
                <p className="text-sm text-muted-foreground">
                  Include your API key in the Authorization header: <code>Bearer your_api_key</code>
                </p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2">Rate Limits</h4>
                <p className="text-sm text-muted-foreground">
                  API calls are limited to 1000 requests per hour per key
                </p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2">Security</h4>
                <p className="text-sm text-muted-foreground">
                  Never expose API keys in client-side code or public repositories
                </p>
              </div>
              <div className="p-4 border rounded-lg">
                <h4 className="font-medium mb-2">Support</h4>
                <p className="text-sm text-muted-foreground">
                  Contact support if you need higher rate limits or custom permissions
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <ToastContainer />
    </div>
  )
}