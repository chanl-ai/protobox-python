"use client"

import { useState, useEffect } from "react"
import { Copy, Check, Plus, Trash2, Key, Globe, RefreshCw, AlertCircle, Calendar, Clock, Infinity } from "lucide-react"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/hooks/use-toast"
import { mcpTokensApi, type MCPToken, type CreateMCPTokenResponse } from "@/lib/api/mcp-tokens"
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

interface MCPTokenDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  workspaceId: string
  mcpUrlPath: string
}

export function MCPTokenDialog({ open, onOpenChange, workspaceId, mcpUrlPath }: MCPTokenDialogProps) {
  const { toast } = useToast()
  const [tokens, setTokens] = useState<MCPToken[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newToken, setNewToken] = useState<CreateMCPTokenResponse | null>(null)
  const [copiedItem, setCopiedItem] = useState<string | null>(null)
  
  // Form state
  const [tokenName, setTokenName] = useState("")
  const [tokenDescription, setTokenDescription] = useState("")
  const [expiresIn, setExpiresIn] = useState<string>("30")
  const [customDays, setCustomDays] = useState<string>("90")

  useEffect(() => {
    if (open && workspaceId) {
      loadTokens()
    }
  }, [open, workspaceId])

  const loadTokens = async () => {
    setLoading(true)
    try {
      const data = await mcpTokensApi.list(workspaceId)
      setTokens(data)
    } catch (error) {
      toast({
        title: "Error loading tokens",
        description: error instanceof Error ? error.message : "Failed to load MCP tokens",
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

  const handleCreateToken = async () => {
    if (!tokenName.trim()) {
      toast({
        title: "Name required",
        description: "Please enter a name for the token",
        variant: "destructive",
      })
      return
    }

    setCreating(true)
    try {
      let expiresInDays: number | undefined
      
      if (expiresIn === "never") {
        expiresInDays = undefined
      } else if (expiresIn === "custom") {
        expiresInDays = parseInt(customDays)
        if (isNaN(expiresInDays) || expiresInDays < 1) {
          toast({
            title: "Invalid custom duration",
            description: "Please enter a valid number of days",
            variant: "destructive",
          })
          setCreating(false)
          return
        }
      } else {
        expiresInDays = parseInt(expiresIn)
      }
      
      const response = await mcpTokensApi.create(workspaceId, {
        name: tokenName,
        description: tokenDescription || undefined,
        expires_in_days: expiresInDays,
      })
      
      setNewToken(response)
      setShowCreateForm(false)
      setTokenName("")
      setTokenDescription("")
      setExpiresIn("30")
      setCustomDays("90")
      
      // Reload tokens list
      await loadTokens()
      
      toast({
        title: "Token created!",
        description: "Save the token now - it won't be shown again",
      })
    } catch (error) {
      toast({
        title: "Failed to create token",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      })
    } finally {
      setCreating(false)
    }
  }

  const handleRevokeToken = async (tokenId: string, tokenName: string) => {
    try {
      await mcpTokensApi.revoke(workspaceId, tokenId)
      await loadTokens()
      toast({
        title: "Token revoked",
        description: `Token "${tokenName}" has been revoked`,
      })
    } catch (error) {
      toast({
        title: "Failed to revoke token",
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

  // Get MCP base URL
  const getMcpBaseUrl = () => {
    if (process.env.NEXT_PUBLIC_MCP_BASE_URL) {
      return process.env.NEXT_PUBLIC_MCP_BASE_URL
    }
    // Use the API URL which matches the backend configuration
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL
    }
    return process.env.NODE_ENV === 'development' 
      ? 'http://localhost:8090'
      : 'http://localhost:8090'
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            MCP Server Connection
          </DialogTitle>
          <DialogDescription>
            Connect AI assistants like Claude and ChatGPT to your workspace using MCP tokens.
          </DialogDescription>
        </DialogHeader>

        {/* MCP Server URL Section */}
        <div className="space-y-3 p-4 border rounded-lg bg-muted/50">
          <div className="flex items-center gap-2">
            <Globe className="h-4 w-4" />
            <h3 className="font-semibold text-sm">MCP Server URL</h3>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Input
                value={`${getMcpBaseUrl()}${mcpUrlPath}`}
                readOnly
                className="font-mono text-xs"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleCopy(`${getMcpBaseUrl()}${mcpUrlPath}`, 'mcp-url')}
              >
                {copiedItem === 'mcp-url' ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Use this URL with a token (created below) to connect AI assistants via MCP protocol.
            </p>
          </div>
        </div>

        {/* New Token Display */}
        {newToken && (
          <Alert className="border-green-500/50 bg-green-50/10">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="space-y-3">
              <p className="font-semibold">New token created! Save it now - it won't be shown again.</p>
              
              <div className="space-y-2">
                <Label className="text-xs">Token</Label>
                <div className="flex items-center gap-2">
                  <Input
                    value={newToken.token}
                    readOnly
                    className="font-mono text-xs"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCopy(newToken.token, 'new-token')}
                  >
                    {copiedItem === 'new-token' ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label className="text-xs">MCP SSE URL (for AI assistants like Claude)</Label>
                <div className="flex items-center gap-2">
                  <Input
                    value={newToken.mcp_url}
                    readOnly
                    className="font-mono text-xs"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCopy(newToken.mcp_url, 'new-url')}
                  >
                    {copiedItem === 'new-url' ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Use this URL to connect AI assistants via MCP protocol
                </p>
              </div>
              
              <Button
                size="sm"
                variant="outline"
                onClick={() => setNewToken(null)}
                className="w-full"
              >
                Done
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Create Token Form */}
        {showCreateForm && !newToken && (
          <div className="space-y-4 border rounded-lg p-4">
            <h3 className="font-semibold">Create New Token</h3>
            
            <div className="space-y-2">
              <Label htmlFor="token-name">Name *</Label>
              <Input
                id="token-name"
                placeholder="e.g., Claude Assistant"
                value={tokenName}
                onChange={(e) => setTokenName(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="token-description">Description (optional)</Label>
              <Textarea
                id="token-description"
                placeholder="What this token is used for..."
                value={tokenDescription}
                onChange={(e) => setTokenDescription(e.target.value)}
                rows={2}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Token Expiration</Label>
              <Tabs value={expiresIn} onValueChange={setExpiresIn} className="w-full">
                <TabsList className="grid w-full grid-cols-5">
                  <TabsTrigger value="7" className="text-xs">
                    <div className="flex flex-col items-center gap-1">
                      <Clock className="h-3 w-3" />
                      <span>7 days</span>
                    </div>
                  </TabsTrigger>
                  <TabsTrigger value="30" className="text-xs">
                    <div className="flex flex-col items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      <span>30 days</span>
                    </div>
                  </TabsTrigger>
                  <TabsTrigger value="90" className="text-xs">
                    <div className="flex flex-col items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      <span>90 days</span>
                    </div>
                  </TabsTrigger>
                  <TabsTrigger value="365" className="text-xs">
                    <div className="flex flex-col items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      <span>1 year</span>
                    </div>
                  </TabsTrigger>
                  <TabsTrigger value="never" className="text-xs">
                    <div className="flex flex-col items-center gap-1">
                      <Infinity className="h-3 w-3" />
                      <span>Never</span>
                    </div>
                  </TabsTrigger>
                </TabsList>
                
                <div className="mt-4 p-3 rounded-lg bg-muted/50">
                  {expiresIn === "7" && (
                    <p className="text-sm text-muted-foreground">
                      <Clock className="inline h-3 w-3 mr-1" />
                      Token will expire in 7 days. Good for short-term testing.
                    </p>
                  )}
                  {expiresIn === "30" && (
                    <p className="text-sm text-muted-foreground">
                      <Calendar className="inline h-3 w-3 mr-1" />
                      Token will expire in 30 days. Recommended for most use cases.
                    </p>
                  )}
                  {expiresIn === "90" && (
                    <p className="text-sm text-muted-foreground">
                      <Calendar className="inline h-3 w-3 mr-1" />
                      Token will expire in 90 days. Good for longer projects.
                    </p>
                  )}
                  {expiresIn === "365" && (
                    <p className="text-sm text-muted-foreground">
                      <Calendar className="inline h-3 w-3 mr-1" />
                      Token will expire in 1 year. For long-term integrations.
                    </p>
                  )}
                  {expiresIn === "never" && (
                    <div className="space-y-2">
                      <p className="text-sm text-muted-foreground">
                        <Infinity className="inline h-3 w-3 mr-1" />
                        Token will never expire. Use with caution.
                      </p>
                      <Alert className="border-yellow-500/50 bg-yellow-50/10">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription className="text-xs">
                          Non-expiring tokens pose a security risk. Consider using a time-limited token instead.
                        </AlertDescription>
                      </Alert>
                    </div>
                  )}
                </div>
              </Tabs>
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Button
                  variant="link"
                  className="text-xs p-0 h-auto"
                  onClick={() => setExpiresIn("custom")}
                >
                  Need a custom duration?
                </Button>
              </div>
              {expiresIn === "custom" && (
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min="1"
                    max="3650"
                    value={customDays}
                    onChange={(e) => setCustomDays(e.target.value)}
                    placeholder="Enter days"
                    className="w-32"
                  />
                  <span className="text-sm text-muted-foreground">days</span>
                </div>
              )}
            </div>
            
            <div className="flex gap-2">
              <Button
                onClick={handleCreateToken}
                disabled={creating || !tokenName.trim()}
                className="flex-1"
              >
                {creating ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Token'
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setShowCreateForm(false)
                  setTokenName("")
                  setTokenDescription("")
                  setExpiresIn("30")
                  setCustomDays("90")
                }}
                disabled={creating}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Tokens List */}
        {!showCreateForm && !newToken && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-semibold">Tokens</h3>
              <Button
                size="sm"
                onClick={() => setShowCreateForm(true)}
              >
                <Plus className="h-4 w-4 mr-2" />
                New Token
              </Button>
            </div>
            
            {loading ? (
              <div className="space-y-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : tokens.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Key className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No tokens created yet</p>
                <p className="text-sm mt-2">Create a token to connect AI assistants to your workspace</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead>Last Used</TableHead>
                    <TableHead>Usage</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tokens.map((token) => (
                    <TableRow key={token.token_id}>
                      <TableCell>
                        <div>
                          <div className="font-medium">{token.name}</div>
                          {token.description && (
                            <div className="text-xs text-muted-foreground">{token.description}</div>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            token.status === 'active' ? 'default' :
                            token.status === 'expired' ? 'secondary' :
                            'destructive'
                          }
                        >
                          {token.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDate(token.created_at)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {token.expires_at ? (
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(token.expires_at)}
                          </div>
                        ) : (
                          <div className="flex items-center gap-1">
                            <Infinity className="h-3 w-3" />
                            <span>Never</span>
                          </div>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">
                        {token.last_used_at ? formatDate(token.last_used_at) : 'Never'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {token.usage_count}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          {token.status === 'active' && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleRevokeToken(token.token_id, token.name)}
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        )}

        {!showCreateForm && !newToken && (
          <DialogFooter className="flex justify-around w-full">
            <Button variant="link" className="text-xs p-0 h-auto" asChild>
              <a href="https://github.com/chanl-ai/protobox-python/blob/main/docs/MCP_ARCHITECTURE.md" target="_blank" rel="noopener noreferrer">
                View MCP Setup Guide →
              </a>
            </Button>
            <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
              <AlertCircle className="h-4 w-4" />
              <span>Tokens cannot be regenerated once created</span>
            </div>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}