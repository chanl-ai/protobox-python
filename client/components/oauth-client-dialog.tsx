"use client"

import { useState, useEffect } from "react"
import { Copy, Check, Plus, Trash2, Shield, Globe, RefreshCw, AlertCircle, ExternalLink } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Alert,
  AlertDescription,
} from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { useToast } from "@/hooks/use-toast"
import { mcpOAuthApi, type MCPOAuthClient, type CreateOAuthClientResponse } from "@/lib/api/mcp-oauth"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface OAuthClientDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  workspaceId: string
}

export function OAuthClientDialog({ open, onOpenChange, workspaceId }: OAuthClientDialogProps) {
  const { toast } = useToast()
  const [clients, setClients] = useState<MCPOAuthClient[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newClient, setNewClient] = useState<CreateOAuthClientResponse | null>(null)
  const [copiedItem, setCopiedItem] = useState<string | null>(null)
  
  // Form state
  const [clientName, setClientName] = useState("")
  const [clientDescription, setClientDescription] = useState("")
  const [redirectUris, setRedirectUris] = useState<string[]>(["http://localhost:3000/callback"])
  const [clientUri, setClientUri] = useState("")
  const [logoUri, setLogoUri] = useState("")
  const [selectedScopes, setSelectedScopes] = useState<string[]>(["mcp:read", "mcp:execute"])

  const availableScopes = [
    { value: "mcp:read", label: "Read", description: "Read access to MCP resources" },
    { value: "mcp:write", label: "Write", description: "Write access to MCP resources" },
    { value: "mcp:execute", label: "Execute", description: "Execute actions and tools" },
    { value: "offline_access", label: "Offline Access", description: "Refresh tokens for long-term access" }
  ]

  useEffect(() => {
    if (open && workspaceId) {
      loadClients()
    }
  }, [open, workspaceId])

  const loadClients = async () => {
    setLoading(true)
    try {
      const data = await mcpOAuthApi.listClients(workspaceId)
      setClients(data)
    } catch (error) {
      toast({
        title: "Error loading OAuth clients",
        description: error instanceof Error ? error.message : "Failed to load OAuth clients",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async (text: string, itemId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedItem(itemId)
      setTimeout(() => setCopiedItem(null), 2000)
      toast({
        title: "Copied!",
        description: "Value copied to clipboard",
      })
    } catch (error) {
      toast({
        title: "Failed to copy",
        description: "Please try again",
        variant: "destructive",
      })
    }
  }

  const handleAddRedirectUri = () => {
    setRedirectUris([...redirectUris, ""])
  }

  const handleRemoveRedirectUri = (index: number) => {
    setRedirectUris(redirectUris.filter((_, i) => i !== index))
  }

  const handleUpdateRedirectUri = (index: number, value: string) => {
    const updated = [...redirectUris]
    updated[index] = value
    setRedirectUris(updated)
  }

  const handleCreateClient = async () => {
    if (!clientName.trim()) {
      toast({
        title: "Name required",
        description: "Please enter a name for the OAuth client",
        variant: "destructive",
      })
      return
    }

    // Validate redirect URIs
    const validUris = redirectUris.filter(uri => uri.trim())
    if (validUris.length === 0) {
      toast({
        title: "Redirect URI required",
        description: "Please provide at least one redirect URI",
        variant: "destructive",
      })
      return
    }

    setCreating(true)
    try {
      const response = await mcpOAuthApi.createClient(workspaceId, {
        client_name: clientName,
        redirect_uris: validUris,
        description: clientDescription || undefined,
        client_uri: clientUri || undefined,
        logo_uri: logoUri || undefined,
        scopes: selectedScopes,
      })
      
      setNewClient(response)
      setShowCreateForm(false)
      // Reset form
      setClientName("")
      setClientDescription("")
      setRedirectUris(["http://localhost:3000/callback"])
      setClientUri("")
      setLogoUri("")
      setSelectedScopes(["mcp:read", "mcp:execute"])
      
      // Reload clients list
      await loadClients()
      
      toast({
        title: "OAuth client created!",
        description: "Save the client secret now - it won't be shown again",
      })
    } catch (error) {
      toast({
        title: "Failed to create OAuth client",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      })
    } finally {
      setCreating(false)
    }
  }

  const handleRevokeClient = async (clientId: string, clientName: string) => {
    try {
      await mcpOAuthApi.revokeClient(workspaceId, clientId)
      await loadClients()
      toast({
        title: "Client revoked",
        description: `OAuth client "${clientName}" has been revoked`,
      })
    } catch (error) {
      toast({
        title: "Failed to revoke client",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      })
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  // Get OAuth base URL
  const getOAuthBaseUrl = () => {
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL
    }
    return process.env.NODE_ENV === 'development' 
      ? 'http://localhost:8090'
      : 'http://localhost:8090'
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            OAuth 2.1 Client Management
          </DialogTitle>
          <DialogDescription>
            Create OAuth clients for third-party applications to access your MCP server securely.
          </DialogDescription>
        </DialogHeader>

        {/* OAuth Server Info */}
        <Card className="bg-muted/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Globe className="h-4 w-4" />
              OAuth 2.1 Authorization Server
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <Label className="text-xs text-muted-foreground">Authorization Endpoint</Label>
                <code className="text-xs block mt-1">{getOAuthBaseUrl()}/admin/api/v1/oauth/authorize</code>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Token Endpoint</Label>
                <code className="text-xs block mt-1">{getOAuthBaseUrl()}/admin/api/v1/oauth/token</code>
              </div>
            </div>
            <div className="text-xs text-muted-foreground">
              PKCE (S256) is required for all authorization flows. See documentation for integration details.
            </div>
          </CardContent>
        </Card>

        {/* New Client Display */}
        {newClient && (
          <Alert className="border-green-500/50 bg-green-50/10">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="space-y-3">
              <p className="font-semibold">OAuth client created! Save these credentials - the secret won't be shown again.</p>
              
              <div className="space-y-2">
                <Label className="text-xs">Client ID</Label>
                <div className="flex items-center gap-2">
                  <Input
                    value={newClient.client_id}
                    readOnly
                    className="font-mono text-xs"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCopy(newClient.client_id, 'client-id')}
                  >
                    {copiedItem === 'client-id' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label className="text-xs">Client Secret (save this now!)</Label>
                <div className="flex items-center gap-2">
                  <Input
                    value={newClient.client_secret}
                    readOnly
                    className="font-mono text-xs"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCopy(newClient.client_secret, 'client-secret')}
                  >
                    {copiedItem === 'client-secret' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
              
              <Button
                size="sm"
                variant="outline"
                onClick={() => setNewClient(null)}
                className="w-full"
              >
                Done - I've saved the credentials
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Create Client Form */}
        {showCreateForm && !newClient && (
          <div className="space-y-4 border rounded-lg p-4">
            <h3 className="font-semibold">Create New OAuth Client</h3>
            
            <div className="space-y-2">
              <Label htmlFor="client-name">Application Name *</Label>
              <Input
                id="client-name"
                placeholder="e.g., My MCP Integration"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="client-description">Description (optional)</Label>
              <Textarea
                id="client-description"
                placeholder="What this OAuth client is used for..."
                value={clientDescription}
                onChange={(e) => setClientDescription(e.target.value)}
                rows={2}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Redirect URIs *</Label>
              <div className="space-y-2">
                {redirectUris.map((uri, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <Input
                      placeholder="https://app.example.com/callback"
                      value={uri}
                      onChange={(e) => handleUpdateRedirectUri(index, e.target.value)}
                    />
                    {redirectUris.length > 1 && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleRemoveRedirectUri(index)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleAddRedirectUri}
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Redirect URI
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Add all URLs where users will be redirected after authorization.
              </p>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="client-uri">Application URL (optional)</Label>
              <Input
                id="client-uri"
                placeholder="https://app.example.com"
                value={clientUri}
                onChange={(e) => setClientUri(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="logo-uri">Logo URL (optional)</Label>
              <Input
                id="logo-uri"
                placeholder="https://app.example.com/logo.png"
                value={logoUri}
                onChange={(e) => setLogoUri(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label>OAuth Scopes</Label>
              <div className="space-y-2">
                {availableScopes.map((scope) => (
                  <div key={scope.value} className="flex items-start gap-2">
                    <Checkbox
                      id={scope.value}
                      checked={selectedScopes.includes(scope.value)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          setSelectedScopes([...selectedScopes, scope.value])
                        } else {
                          setSelectedScopes(selectedScopes.filter(s => s !== scope.value))
                        }
                      }}
                    />
                    <div className="flex-1">
                      <Label htmlFor={scope.value} className="text-sm font-medium">
                        {scope.label}
                      </Label>
                      <p className="text-xs text-muted-foreground">{scope.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            <Alert>
              <Shield className="h-4 w-4" />
              <AlertDescription className="text-xs">
                <strong>Security Note:</strong> OAuth clients are owned by you and can only access your workspace. 
                PKCE is required for all authorization flows.
              </AlertDescription>
            </Alert>
            
            <div className="flex gap-2">
              <Button
                onClick={handleCreateClient}
                disabled={creating || !clientName.trim() || redirectUris.filter(u => u.trim()).length === 0}
                className="flex-1"
              >
                {creating ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create OAuth Client'
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setShowCreateForm(false)
                  setClientName("")
                  setClientDescription("")
                  setRedirectUris(["http://localhost:3000/callback"])
                  setClientUri("")
                  setLogoUri("")
                  setSelectedScopes(["mcp:read", "mcp:execute"])
                }}
                disabled={creating}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Clients List */}
        {!showCreateForm && !newClient && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-semibold">Your OAuth Clients</h3>
              <Button
                size="sm"
                onClick={() => setShowCreateForm(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                New Client
              </Button>
            </div>
            
            {loading ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : clients.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No OAuth clients created yet</p>
                <p className="text-sm mt-2">Create an OAuth client to enable third-party access to your MCP server</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Application</TableHead>
                    <TableHead>Client ID</TableHead>
                    <TableHead>Scopes</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Last Used</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clients.map((client) => (
                    <TableRow key={client.client_id}>
                      <TableCell>
                        <div>
                          <div className="font-medium flex items-center gap-2">
                            {client.client_name}
                            {client.client_uri && (
                              <a
                                href={client.client_uri}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-muted-foreground hover:text-primary"
                              >
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                          </div>
                          {client.description && (
                            <div className="text-xs text-muted-foreground">{client.description}</div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <code className="text-xs">{client.client_id.substring(0, 12)}...</code>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 w-6 p-0"
                            onClick={() => handleCopy(client.client_id, `copy-${client.client_id}`)}
                          >
                            {copiedItem === `copy-${client.client_id}` ? (
                              <Check className="h-3 w-3" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1 flex-wrap">
                          {client.allowed_scopes.map(scope => (
                            <Badge key={scope} variant="secondary" className="text-xs">
                              {scope.replace('mcp:', '')}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={client.status === 'active' ? 'default' : 'destructive'}
                        >
                          {client.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDate(client.created_at)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {client.last_used_at ? formatDate(client.last_used_at) : 'Never'}
                      </TableCell>
                      <TableCell className="text-right">
                        {client.status === 'active' && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleRevokeClient(client.client_id, client.client_name)}
                            className="text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        )}

        {!showCreateForm && !newClient && (
          <DialogFooter className="flex justify-between items-center">
            <Button variant="link" className="text-xs p-0 h-auto" asChild>
              <a href="https://github.com/chanl-ai/protobox-python/blob/main/docs/OAUTH_IMPLEMENTATION.md" target="_blank" rel="noopener noreferrer">
                View OAuth Integration Guide →
              </a>
            </Button>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Shield className="h-4 w-4" />
              <span>Each client is owned by you and scoped to this workspace</span>
            </div>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}