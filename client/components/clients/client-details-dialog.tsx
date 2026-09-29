"use client"

import { useState, useEffect } from "react"
import { Copy, Check, ChevronRight, FileCode, Terminal, Settings, BookOpen, Zap, ExternalLink, Trash2, Plus, Shield } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useToast } from "@/hooks/use-toast"
import { mcpTokensApi } from "@/lib/api/mcp-tokens"
import { mcpOAuthApi, type CreateOAuthClientResponse, type MCPOAuthClient } from "@/lib/api/mcp-oauth"
import { useAuthStore } from "@/lib/auth/stores/auth.store"
import { AVAILABLE_OAUTH_SCOPES } from "@/lib/constants/oauth-scopes"

interface ClientDetailsDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  client: {
    title: string
    description: string
    icon: string | React.ReactNode
    setupSteps?: string[]
    configTemplate?: (url: string, token: string) => string
    oauthConfigTemplate?: (serverUrl: string, clientId: string) => string
    codeExamples?: {
      language: string
      label: string
      code: (url: string, token: string) => string
    }[]
    documentation?: string
    requirements?: string[]
    supportsOAuth?: boolean
    redirectUris?: string[]
    clientType?: 'public' | 'confidential'
  }
}

export function ClientDetailsDialog({ open, onOpenChange, client }: ClientDetailsDialogProps) {
  const { currentWorkspace } = useAuthStore()
  const { toast } = useToast()
  const [copiedItem, setCopiedItem] = useState<string | null>(null)
  const [selectedToken, setSelectedToken] = useState<string>("")
  const [tokens, setTokens] = useState<any[]>([])
  const [selectedLanguage, setSelectedLanguage] = useState<string>("javascript")
  
  // OAuth-specific state
  const [oauthClient, setOauthClient] = useState<CreateOAuthClientResponse | null>(null)
  const [creatingOAuthClient, setCreatingOAuthClient] = useState(false)
  const [setupMode, setSetupMode] = useState<'oauth' | 'token'>('oauth')
  const [customRedirectUris, setCustomRedirectUris] = useState<string[]>(['https://yourapp.com/auth/callback'])
  const [customClientName, setCustomClientName] = useState('Custom MCP Client')
  
  // New state for enhanced Custom Integration
  const [existingClients, setExistingClients] = useState<MCPOAuthClient[]>([])
  const [selectedExistingClient, setSelectedExistingClient] = useState<string>('')
  const [customOAuthMode, setCustomOAuthMode] = useState<'existing' | 'create'>('existing')
  const [customClientDescription, setCustomClientDescription] = useState('')
  const [customSelectedScopes, setCustomSelectedScopes] = useState<string[]>(['mcp:read', 'mcp:execute'])
  
  // New state for non-custom OAuth integrations
  const [standardOAuthMode, setStandardOAuthMode] = useState<'existing' | 'create'>('existing')
  const [selectedStandardClient, setSelectedStandardClient] = useState<string>('')
  const [standardSelectedScopes, setStandardSelectedScopes] = useState<string[]>(['mcp:read', 'mcp:execute'])
  
  // WorkspaceLoadingGuard ensures currentWorkspace exists when used in dashboard
  const workspaceId = currentWorkspace!.id
  
  useEffect(() => {
    if (open && workspaceId) {
      loadTokens()
      // Reset OAuth state when dialog opens
      setOauthClient(null)
      setSetupMode(client.supportsOAuth ? 'oauth' : 'token')
      
      if (client.supportsOAuth) {
        loadExistingClients()
        
        // Reset for Custom Integration
        if (client.title === 'Custom Integration') {
          setCustomRedirectUris(['https://yourapp.com/auth/callback'])
          setCustomClientName('Custom MCP Client')
          setCustomClientDescription('')
          setCustomSelectedScopes(['mcp:read', 'mcp:execute'])
          setCustomOAuthMode('existing')
          setSelectedExistingClient('')
        } else {
          // Reset for standard OAuth integrations
          setStandardOAuthMode('existing')
          setSelectedStandardClient('')
          setStandardSelectedScopes(['mcp:read', 'mcp:execute'])
        }
      }
    }
  }, [open, workspaceId, client.supportsOAuth, client.title])

  const loadTokens = async () => {
    try {
      const data = await mcpTokensApi.list(workspaceId)
      const activeTokens = data.filter(t => t.status === 'active')
      setTokens(activeTokens)
      if (activeTokens.length > 0 && !selectedToken) {
        setSelectedToken(activeTokens[0].token_id)
      }
    } catch (error) {
      console.error("Failed to load tokens:", error)
    }
  }

  const loadExistingClients = async () => {
    try {
      const data = await mcpOAuthApi.listClients(workspaceId)
      const activeClients = data.filter(c => c.status === 'active')
      setExistingClients(activeClients)
      
      if (client.title === 'Custom Integration') {
        // For Custom Integration, select first available client
        if (activeClients.length > 0 && !selectedExistingClient) {
          setSelectedExistingClient(activeClients[0].client_id)
        }
      } else {
        // For standard integrations, auto-select client by name pattern
        const expectedClientName = `${client.title} OAuth Client`
        const matchingClient = activeClients.find(c => c.client_name === expectedClientName)
        
        if (matchingClient) {
          setSelectedStandardClient(matchingClient.client_id)
          setStandardOAuthMode('existing')
        } else if (activeClients.length > 0) {
          // Fallback to first client if no exact match
          setSelectedStandardClient(activeClients[0].client_id)
          setStandardOAuthMode('existing')
        } else {
          // No clients available, default to create mode
          setStandardOAuthMode('create')
        }
      }
    } catch (error) {
      console.error("Failed to load existing OAuth clients:", error)
    }
  }

  const createOAuthClient = async () => {
    if (!client.supportsOAuth) return
    
    setCreatingOAuthClient(true)
    try {
      // Use custom redirect URIs for Custom Integration, otherwise use predefined ones
      const redirectUris = client.title === 'Custom Integration' 
        ? customRedirectUris.filter(uri => uri.trim())
        : client.redirectUris || []
      
      // Determine the type of integration and mode
      const isCustomIntegration = client.title === 'Custom Integration'
      const isCustomIntegrationCreate = isCustomIntegration && customOAuthMode === 'create'
      const isStandardIntegrationCreate = !isCustomIntegration && standardOAuthMode === 'create'
      
      const response = await mcpOAuthApi.createClient(workspaceId, {
        client_name: isCustomIntegrationCreate ? customClientName : 
                    isCustomIntegration ? customClientName : 
                    `${client.title} OAuth Client`,
        description: isCustomIntegrationCreate ? customClientDescription :
                    isCustomIntegration ? `Custom OAuth client for MCP integration` : 
                    `OAuth client for ${client.title} MCP integration`,
        redirect_uris: redirectUris,
        scopes: isCustomIntegrationCreate ? customSelectedScopes : 
               isStandardIntegrationCreate ? standardSelectedScopes :
               ['mcp:read', 'mcp:execute', 'mcp:write'],
        client_type: client.clientType || 'public',
        token_endpoint_auth_method: client.clientType === 'confidential' ? 'client_secret_basic' : 'none'
      })
      
      setOauthClient(response)
      
      // Reload existing clients and update selection
      await loadExistingClients()
      
      if (client.title === 'Custom Integration') {
        setCustomOAuthMode('existing')
        setSelectedExistingClient(response.client_id)
      } else {
        setStandardOAuthMode('existing')
        setSelectedStandardClient(response.client_id)
      }
      
      toast({
        title: "OAuth Client Created",
        description: `OAuth client for ${client.title} has been created successfully`,
      })
    } catch (error) {
      toast({
        title: "Error creating OAuth client",
        description: error instanceof Error ? error.message : "Failed to create OAuth client",
        variant: "destructive",
      })
    } finally {
      setCreatingOAuthClient(false)
    }
  }
  
  const getMcpBaseUrl = () => {
    if (process.env.NEXT_PUBLIC_MCP_BASE_URL) {
      return process.env.NEXT_PUBLIC_MCP_BASE_URL
    }
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL
    }
    return process.env.NODE_ENV === 'development' 
      ? 'http://localhost:8090'
      : 'http://localhost:8090'
  }
  
  const handleCopy = async (text: string, itemId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedItem(itemId)
      setTimeout(() => setCopiedItem(null), 2000)
      toast({
        title: "Copied!",
        description: "Configuration copied to clipboard",
      })
    } catch (error) {
      toast({
        title: "Failed to copy",
        description: "Please try again",
        variant: "destructive",
      })
    }
  }

  const renderIcon = () => {
    if (typeof client.icon === "string") {
      return <img src={client.icon} alt="" className="h-6 w-6" />
    }
    return client.icon
  }

  // Default setup steps if none provided
  const defaultSetupSteps = [
    "Create an MCP token in Settings → API",
    "Copy the configuration below",
    "Add it to your client application",
    "Test the connection"
  ]

  const setupSteps = client.setupSteps || defaultSetupSteps

  // Default code examples if none provided
  const defaultCodeExamples = client.codeExamples || [
    {
      language: "javascript",
      label: "JavaScript/TypeScript",
      code: (url: string, token: string) => `// Install MCP client
// npm install @mcp/client

import { MCPClient } from '@mcp/client';

const client = new MCPClient({
  url: '${url}',
  token: '${token}'
});

await client.connect();
const tools = await client.listTools();`
    },
    {
      language: "python",
      label: "Python",
      code: (url: string, token: string) => `# Install MCP client
# pip install mcp-client

from mcp_client import MCPClient

client = MCPClient(
    url="${url}",
    token="${token}"
)

client.connect()
tools = client.list_tools()`
    },
    {
      language: "curl",
      label: "cURL",
      code: (url: string, token: string) => `curl -X GET \\
  "${url}" \\
  -H "Authorization: Bearer ${token}" \\
  -H "Accept: text/event-stream"`
    }
  ]

  const selectedExample = defaultCodeExamples.find(ex => ex.language === selectedLanguage) || defaultCodeExamples[0]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <div className="h-10 w-10 shrink-0 rounded-lg bg-muted flex items-center justify-center">
              {renderIcon()}
            </div>
            <div>
              <div>{client.title}</div>
              <DialogDescription className="mt-1">
                {client.description}
              </DialogDescription>
            </div>
          </DialogTitle>
        </DialogHeader>
        
        <Tabs defaultValue="oauth" className="mt-6">
          <TabsList className="grid w-full grid-cols-4">
            {client.supportsOAuth && (
              <TabsTrigger value="oauth">
                <Zap className="h-4 w-4 mr-2" />
                OAuth Setup
              </TabsTrigger>
            )}
            <TabsTrigger value="setup">
              <Settings className="h-4 w-4 mr-2" />
              {client.supportsOAuth ? 'Manual Setup' : 'Setup'}
            </TabsTrigger>
            <TabsTrigger value="code">
              <FileCode className="h-4 w-4 mr-2" />
              Code Examples
            </TabsTrigger>
            <TabsTrigger value="docs">
              <BookOpen className="h-4 w-4 mr-2" />
              Documentation
            </TabsTrigger>
          </TabsList>

          {client.supportsOAuth && (
            <TabsContent value="oauth" className="space-y-6 mt-6">
              <div className="space-y-4">
                <div className="rounded-lg bg-blue-50 dark:bg-blue-950 p-4">
                  <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                    🚀 Recommended: OAuth Setup
                  </h4>
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    OAuth provides a more secure and user-friendly way to connect {client.title} to your MCP server. 
                    No manual token management required!
                  </p>
                </div>

                {!oauthClient ? (
                  <div className="space-y-4">
                    {client.title === 'Custom Integration' ? (
                      // Custom Integration - Two-tab OAuth setup
                      <div className="space-y-4">
                        <Tabs value={customOAuthMode} onValueChange={(value) => setCustomOAuthMode(value as 'existing' | 'create')}>
                          <TabsList className="grid w-full grid-cols-2">
                            <TabsTrigger value="existing">Select Existing Client</TabsTrigger>
                            <TabsTrigger value="create">Create New Client</TabsTrigger>
                          </TabsList>
                          
                          <TabsContent value="existing" className="space-y-4 mt-4">
                            {existingClients.length === 0 ? (
                              <div className="text-center py-6 text-muted-foreground">
                                <Shield className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                <p>No OAuth clients found</p>
                                <p className="text-sm mt-1">Create one in the "Create New Client" tab</p>
                              </div>
                            ) : (
                              <div className="space-y-4">
                                <div className="space-y-2">
                                  <Label>Select OAuth Client</Label>
                                  <Select value={selectedExistingClient} onValueChange={setSelectedExistingClient}>
                                    <SelectTrigger>
                                      <SelectValue placeholder="Choose an existing client" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {existingClients.map(client => (
                                        <SelectItem key={client.client_id} value={client.client_id}>
                                          {client.client_name}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </div>
                                
                                {selectedExistingClient && (() => {
                                  const selectedClient = existingClients.find(c => c.client_id === selectedExistingClient)
                                  if (!selectedClient) return null
                                  
                                  return (
                                    <div className="space-y-3 p-4 border rounded-lg bg-muted/20">
                                      <h4 className="font-medium">Client Details</h4>
                                      
                                      <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div>
                                          <Label className="text-xs text-muted-foreground">Client ID</Label>
                                          <div className="flex items-center gap-2 mt-1">
                                            <code className="text-xs bg-background px-2 py-1 rounded">{selectedClient.client_id}</code>
                                            <Button
                                              size="sm"
                                              variant="ghost"
                                              className="h-6 w-6 p-0"
                                              onClick={() => handleCopy(selectedClient.client_id, 'existing-client-id')}
                                            >
                                              {copiedItem === 'existing-client-id' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                                            </Button>
                                          </div>
                                        </div>
                                        
                                        <div>
                                          <Label className="text-xs text-muted-foreground">Created</Label>
                                          <p className="text-xs mt-1">{new Date(selectedClient.created_at).toLocaleDateString()}</p>
                                        </div>
                                      </div>
                                      
                                      {selectedClient.description && (
                                        <div>
                                          <Label className="text-xs text-muted-foreground">Description</Label>
                                          <p className="text-xs mt-1">{selectedClient.description}</p>
                                        </div>
                                      )}
                                      
                                      <div>
                                        <Label className="text-xs text-muted-foreground">Scopes</Label>
                                        <div className="flex gap-1 mt-1 flex-wrap">
                                          {selectedClient.allowed_scopes.map(scope => (
                                            <Badge key={scope} variant="secondary" className="text-xs">
                                              {scope.replace('mcp:', '')}
                                            </Badge>
                                          ))}
                                        </div>
                                      </div>
                                      
                                      <div>
                                        <Label className="text-xs text-muted-foreground">Redirect URIs ({selectedClient.redirect_uris.length})</Label>
                                        <div className="mt-1 space-y-1">
                                          {selectedClient.redirect_uris.slice(0, 3).map((uri, index) => (
                                            <code key={index} className="text-xs bg-background px-2 py-1 rounded block">{uri}</code>
                                          ))}
                                          {selectedClient.redirect_uris.length > 3 && (
                                            <p className="text-xs text-muted-foreground">+{selectedClient.redirect_uris.length - 3} more</p>
                                          )}
                                        </div>
                                      </div>
                                    </div>
                                  )
                                })()}
                              </div>
                            )}
                          </TabsContent>
                          
                          <TabsContent value="create" className="space-y-4 mt-4">
                            <div className="space-y-4">
                              <div>
                                <Label className="text-sm font-medium">Client Name *</Label>
                                <Input
                                  placeholder="e.g., My MCP Integration"
                                  value={customClientName}
                                  onChange={(e) => setCustomClientName(e.target.value)}
                                  className="mt-1"
                                />
                              </div>
                              
                              <div>
                                <Label className="text-sm font-medium">Description</Label>
                                <Textarea
                                  placeholder="What this OAuth client is used for..."
                                  value={customClientDescription}
                                  onChange={(e) => setCustomClientDescription(e.target.value)}
                                  className="mt-1"
                                  rows={2}
                                />
                              </div>
                              
                              <div className="space-y-2">
                                <Label className="text-sm font-medium">Redirect URIs *</Label>
                                {customRedirectUris.map((uri, index) => (
                                  <div key={index} className="flex items-center gap-2">
                                    <Input
                                      placeholder="https://yourapp.com/auth/callback"
                                      value={uri}
                                      onChange={(e) => {
                                        const updated = [...customRedirectUris]
                                        updated[index] = e.target.value
                                        setCustomRedirectUris(updated)
                                      }}
                                      className="flex-1"
                                    />
                                    {customRedirectUris.length > 1 && (
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => {
                                          setCustomRedirectUris(customRedirectUris.filter((_, i) => i !== index))
                                        }}
                                      >
                                        <Trash2 className="h-4 w-4" />
                                      </Button>
                                    )}
                                  </div>
                                ))}
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => setCustomRedirectUris([...customRedirectUris, ""])}
                                  className="w-full"
                                >
                                  <Plus className="h-4 w-4 mr-2" />
                                  Add Redirect URI
                                </Button>
                              </div>
                              
                              <div>
                                <Label className="text-sm font-medium">OAuth Scopes *</Label>
                                <div className="space-y-2 mt-2">
                                  {AVAILABLE_OAUTH_SCOPES.map((scope) => (
                                    <div key={scope.value} className="flex items-start gap-2">
                                      <Checkbox
                                        id={`custom-${scope.value}`}
                                        checked={customSelectedScopes.includes(scope.value)}
                                        onCheckedChange={(checked) => {
                                          if (checked) {
                                            setCustomSelectedScopes([...customSelectedScopes, scope.value])
                                          } else {
                                            setCustomSelectedScopes(customSelectedScopes.filter(s => s !== scope.value))
                                          }
                                        }}
                                      />
                                      <div className="flex-1">
                                        <Label htmlFor={`custom-${scope.value}`} className="text-sm font-medium cursor-pointer">
                                          {scope.label}
                                        </Label>
                                        <p className="text-xs text-muted-foreground">{scope.description}</p>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                              
                              <div className="text-xs text-muted-foreground bg-muted/50 p-3 rounded">
                                <p className="font-medium mb-1">Common callback URLs:</p>
                                <ul className="space-y-1">
                                  <li>• <code>https://yourapp.com/auth/callback</code> - Production app</li>
                                  <li>• <code>https://yourapp.vercel.app/auth/callback</code> - Vercel deployment</li>
                                </ul>
                              </div>
                              
                              <Button 
                                onClick={createOAuthClient}
                                disabled={creatingOAuthClient || !customClientName.trim() || customRedirectUris.filter(uri => uri.trim()).length === 0 || customSelectedScopes.length === 0}
                                className="w-full"
                              >
                                {creatingOAuthClient ? (
                                  "Creating OAuth Client..."
                                ) : (
                                  <>
                                    <Zap className="h-4 w-4 mr-2" />
                                    Create OAuth Client
                                  </>
                                )}
                              </Button>
                            </div>
                          </TabsContent>
                        </Tabs>
                      </div>
                    ) : (
                      // Standard OAuth integrations - Select existing or create new
                      <div className="space-y-4">
                        <div className="space-y-3">
                          <Label>Step 1: OAuth Client</Label>
                          <p className="text-sm text-muted-foreground">
                            Use an existing OAuth client or create a new one for {client.title}.
                          </p>
                          
                          <div className="space-y-3">
                            <div className="flex items-center gap-2">
                              <input
                                type="radio"
                                id="existing-standard"
                                name="standard-oauth-mode"
                                checked={standardOAuthMode === 'existing'}
                                onChange={() => setStandardOAuthMode('existing')}
                                className="w-4 h-4"
                              />
                              <Label htmlFor="existing-standard" className="text-sm font-medium cursor-pointer">
                                Use existing client
                              </Label>
                            </div>
                            
                            {standardOAuthMode === 'existing' && (
                              <div className="ml-6 space-y-2">
                                {existingClients.length === 0 ? (
                                  <p className="text-sm text-muted-foreground">No OAuth clients found. Create one below.</p>
                                ) : (
                                  <>
                                    <Select value={selectedStandardClient} onValueChange={setSelectedStandardClient}>
                                      <SelectTrigger>
                                        <SelectValue placeholder="Choose an existing client" />
                                      </SelectTrigger>
                                      <SelectContent>
                                        {existingClients.map(client => (
                                          <SelectItem key={client.client_id} value={client.client_id}>
                                            {client.client_name}
                                          </SelectItem>
                                        ))}
                                      </SelectContent>
                                    </Select>
                                    {selectedStandardClient && (
                                      <Button 
                                        onClick={() => {
                                          // Set oauthClient to simulate selection for configuration display
                                          const selectedClient = existingClients.find(c => c.client_id === selectedStandardClient)
                                          if (selectedClient) {
                                            setOauthClient({
                                              client_id: selectedClient.client_id,
                                              client_name: selectedClient.client_name,
                                              redirect_uris: selectedClient.redirect_uris,
                                              allowed_scopes: selectedClient.allowed_scopes,
                                              created_at: selectedClient.created_at,
                                              client_secret: "", // Existing clients don't expose their secret
                                              message: "Using existing OAuth client"
                                            })
                                          }
                                        }}
                                        className="w-full"
                                        disabled={!selectedStandardClient}
                                      >
                                        <ChevronRight className="h-4 w-4 mr-2" />
                                        Proceed with Selected Client
                                      </Button>
                                    )}
                                  </>
                                )}
                              </div>
                            )}
                            
                            <div className="flex items-center gap-2">
                              <input
                                type="radio"
                                id="create-standard"
                                name="standard-oauth-mode"
                                checked={standardOAuthMode === 'create'}
                                onChange={() => setStandardOAuthMode('create')}
                                className="w-4 h-4"
                              />
                              <Label htmlFor="create-standard" className="text-sm font-medium cursor-pointer">
                                Create new client
                              </Label>
                            </div>
                            
                            {standardOAuthMode === 'create' && (
                              <div className="ml-6 space-y-3">
                                <div>
                                  <Label className="text-sm font-medium">OAuth Scopes *</Label>
                                  <div className="space-y-2 mt-2">
                                    {AVAILABLE_OAUTH_SCOPES.map((scope) => (
                                      <div key={scope.value} className="flex items-start gap-2">
                                        <Checkbox
                                          id={`standard-${scope.value}`}
                                          checked={standardSelectedScopes.includes(scope.value)}
                                          onCheckedChange={(checked) => {
                                            if (checked) {
                                              setStandardSelectedScopes([...standardSelectedScopes, scope.value])
                                            } else {
                                              setStandardSelectedScopes(standardSelectedScopes.filter(s => s !== scope.value))
                                            }
                                          }}
                                        />
                                        <div className="flex-1">
                                          <Label htmlFor={`standard-${scope.value}`} className="text-sm font-medium cursor-pointer">
                                            {scope.label}
                                          </Label>
                                          <p className="text-xs text-muted-foreground">{scope.description}</p>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                                
                                <Button 
                                  onClick={createOAuthClient}
                                  disabled={creatingOAuthClient || standardSelectedScopes.length === 0}
                                  className="w-full"
                                >
                                  {creatingOAuthClient ? (
                                    "Creating OAuth Client..."
                                  ) : (
                                    <>
                                      <Zap className="h-4 w-4 mr-2" />
                                      Create OAuth Client for {client.title}
                                    </>
                                  )}
                                </Button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {(() => {
                      // For Custom Integration, show success for either created client or selected existing client
                      if (client.title === 'Custom Integration') {
                        if (oauthClient) {
                          // Newly created client
                          return (
                            <div className="rounded-lg bg-green-50 dark:bg-green-950 p-4">
                              <div className="flex items-center gap-2 mb-2">
                                <Check className="h-4 w-4 text-green-600" />
                                <h4 className="font-medium text-green-900 dark:text-green-100">
                                  OAuth Client Created Successfully!
                                </h4>
                              </div>
                              <p className="text-sm text-green-700 dark:text-green-300">
                                Client ID: <code className="bg-green-100 dark:bg-green-900 px-1 rounded">{oauthClient.client_id}</code>
                              </p>
                            </div>
                          )
                        } else if (selectedExistingClient && existingClients.find(c => c.client_id === selectedExistingClient)) {
                          // Selected existing client
                          const selectedClient = existingClients.find(c => c.client_id === selectedExistingClient)!
                          return (
                            <div className="rounded-lg bg-blue-50 dark:bg-blue-950 p-4">
                              <div className="flex items-center gap-2 mb-2">
                                <Check className="h-4 w-4 text-blue-600" />
                                <h4 className="font-medium text-blue-900 dark:text-blue-100">
                                  Using Existing OAuth Client
                                </h4>
                              </div>
                              <p className="text-sm text-blue-700 dark:text-blue-300">
                                Client: <strong>{selectedClient.client_name}</strong> • ID: <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">{selectedClient.client_id}</code>
                              </p>
                            </div>
                          )
                        }
                        return null
                      } else {
                        // Standard clients - show created client success
                        return (
                          <div className="rounded-lg bg-green-50 dark:bg-green-950 p-4">
                            <div className="flex items-center gap-2 mb-2">
                              <Check className="h-4 w-4 text-green-600" />
                              <h4 className="font-medium text-green-900 dark:text-green-100">
                                OAuth Client Created Successfully!
                              </h4>
                            </div>
                            <p className="text-sm text-green-700 dark:text-green-300">
                              Client ID: <code className="bg-green-100 dark:bg-green-900 px-1 rounded">{oauthClient.client_id}</code>
                            </p>
                          </div>
                        )
                      }
                    })()}

                    <div className="space-y-3">
                      <Label>Step 2: Configure {client.title}</Label>
                      {(() => {
                        // Get the client ID to use (either from newly created client or selected existing client)
                        const clientIdToUse = client.title === 'Custom Integration' 
                          ? (oauthClient?.client_id || selectedExistingClient)
                          : (oauthClient?.client_id || selectedStandardClient)
                        
                        if (!clientIdToUse) return null
                        
                        return client.oauthConfigTemplate ? (
                          <div className="relative">
                            <pre className="p-4 rounded-lg bg-muted text-xs overflow-x-auto">
                              <code>
                                {client.oauthConfigTemplate(
                                  `${getMcpBaseUrl()}/mcp/${workspaceId}/sse`,
                                  clientIdToUse
                                )}
                              </code>
                            </pre>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="absolute top-2 right-2"
                              onClick={() => handleCopy(
                                client.oauthConfigTemplate!(
                                  `${getMcpBaseUrl()}/mcp/${workspaceId}/sse`,
                                  clientIdToUse
                                ),
                                'oauth-config'
                              )}
                            >
                              {copiedItem === 'oauth-config' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                            </Button>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            <p className="text-sm text-muted-foreground">
                              Use these details to configure {client.title}:
                            </p>
                            <div className="space-y-2">
                              <div className="flex items-center gap-2">
                                <Label className="min-w-24">Server URL:</Label>
                                <code className="flex-1 p-2 bg-muted rounded text-sm">{`${getMcpBaseUrl()}/mcp/${workspaceId}/sse`}</code>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleCopy(`${getMcpBaseUrl()}/mcp/${workspaceId}/sse`, 'oauth-server-url')}
                                >
                                  {copiedItem === 'oauth-server-url' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                </Button>
                              </div>
                              <div className="flex items-center gap-2">
                                <Label className="min-w-24">Client ID:</Label>
                                <code className="flex-1 p-2 bg-muted rounded text-sm">{clientIdToUse}</code>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleCopy(clientIdToUse, 'oauth-client-id')}
                                >
                                  {copiedItem === 'oauth-client-id' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                                </Button>
                              </div>
                            </div>
                          </div>
                        )
                      })()}
                    </div>

                    <div className="space-y-3">
                      <Label>Step 3: Test & Authorize</Label>
                      <p className="text-sm text-muted-foreground">
                        {client.title === 'Custom Integration' 
                          ? 'Test the OAuth flow with MCP Inspector or your custom client. The client will auto-discover endpoints and prompt for authorization.'
                          : `${client.title} will prompt you to authorize access when you first connect. Click "Authorize" to grant permission.`
                        }
                      </p>
                      
                      {client.title === 'Custom Integration' && (() => {
                        const clientIdToUse = oauthClient?.client_id || selectedExistingClient
                        if (!clientIdToUse) return null
                        
                        return (
                          <div className="grid grid-cols-2 gap-2">
                            <Button 
                              variant="outline"
                              className="w-full"
                              onClick={() => {
                                const authUrl = `${getMcpBaseUrl()}/authorize?client_id=${clientIdToUse}&response_type=code&scope=mcp:read mcp:execute`
                                window.open(authUrl, '_blank')
                              }}
                            >
                              <ExternalLink className="h-4 w-4 mr-2" />
                              Test Auth Flow
                            </Button>
                            <Button 
                              variant="outline"
                              className="w-full"
                              onClick={() => {
                                const discoveryUrl = `${getMcpBaseUrl()}/.well-known/oauth-authorization-server`
                                window.open(discoveryUrl, '_blank')
                              }}
                            >
                              <ExternalLink className="h-4 w-4 mr-2" />
                              View Discovery
                            </Button>
                          </div>
                        )
                      })()}
                      
                      {client.title !== 'Custom Integration' && (() => {
                        const clientIdToUse = oauthClient?.client_id || selectedStandardClient
                        if (!clientIdToUse) return null
                        
                        return (
                          <Button 
                            variant="outline" 
                            className="w-full"
                            onClick={() => {
                              const authUrl = `${getMcpBaseUrl()}/authorize?client_id=${clientIdToUse}&response_type=code&scope=mcp:read mcp:execute`
                              window.open(authUrl, '_blank')
                            }}
                          >
                            <ExternalLink className="h-4 w-4 mr-2" />
                            Test Authorization Flow
                          </Button>
                        )
                      })()}
                    </div>

                    {client.title === 'Custom Integration' && (() => {
                      const clientIdToUse = oauthClient?.client_id || selectedExistingClient
                      if (!clientIdToUse) return null
                      
                      return (
                        <div className="mt-6 p-4 border rounded-lg bg-blue-50 dark:bg-blue-950">
                          <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                            🔍 Test with MCP Inspector
                          </h4>
                          <div className="space-y-3 text-sm text-blue-700 dark:text-blue-300">
                            <div className="space-y-2">
                              <p><strong>Step 1:</strong> Open <a href="https://mcp-inspector.modelcontextprotocol.io" target="_blank" rel="noopener noreferrer" className="underline font-medium">MCP Inspector</a></p>
                              <p><strong>Step 2:</strong> Add new connection → Choose "OAuth 2.0"</p>
                              <p><strong>Step 3:</strong> Enter Server URL:</p>
                              <div className="bg-blue-100 dark:bg-blue-900 p-2 rounded">
                                <code className="text-xs">{`${getMcpBaseUrl()}/mcp`}</code>
                              </div>
                              <p><strong>Step 4:</strong> Enter Client ID:</p>
                              <div className="bg-blue-100 dark:bg-blue-900 p-2 rounded">
                                <code className="text-xs">{clientIdToUse}</code>
                              </div>
                            <p><strong>Step 5:</strong> Click "Connect" - MCP Inspector will:</p>
                            <ul className="list-disc list-inside ml-4 space-y-1 text-xs">
                              <li>Auto-discover OAuth endpoints</li>
                              <li>Open browser for authorization</li>
                              <li>Redirect back with access token</li>
                              <li>Connect to your MCP server</li>
                            </ul>
                          </div>
                          
                          <div className="bg-yellow-50 dark:bg-yellow-950 p-2 rounded border border-yellow-200 dark:border-yellow-800">
                            <p className="text-xs text-yellow-800 dark:text-yellow-200">
                              <strong>⚠️ Important:</strong> Direct connections without OAuth will show "401 Unauthorized" - this is expected! You must complete the OAuth flow first.
                            </p>
                          </div>
                          
                            <Button 
                              variant="outline"
                              size="sm"
                              className="w-full bg-blue-100 dark:bg-blue-900 border-blue-200 dark:border-blue-800 hover:bg-blue-200 dark:hover:bg-blue-800"
                              onClick={() => {
                                window.open('https://mcp-inspector.modelcontextprotocol.io', '_blank')
                              }}
                            >
                              <ExternalLink className="h-4 w-4 mr-2" />
                              Open MCP Inspector
                            </Button>
                          </div>
                        </div>
                      )
                    })()}
                  </div>
                )}
              </div>
            </TabsContent>
          )}

          <TabsContent value="setup" className="space-y-6 mt-6">
            {/* Requirements */}
            {client.requirements && (
              <div className="space-y-3">
                <Label>Requirements</Label>
                <div className="rounded-lg bg-muted/50 p-4">
                  <ul className="space-y-2">
                    {client.requirements.map((req, index) => (
                      <li key={index} className="flex items-start gap-2 text-sm">
                        <ChevronRight className="h-4 w-4 mt-0.5 text-muted-foreground" />
                        <span>{req}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Token Selection */}
            <div className="space-y-2">
              <Label>Select MCP Token</Label>
              <Select value={selectedToken} onValueChange={setSelectedToken}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a token" />
                </SelectTrigger>
                <SelectContent>
                  {tokens.map(token => (
                    <SelectItem key={token.token_id} value={token.token_id}>
                      {token.name} - Created {new Date(token.created_at).toLocaleDateString()}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {tokens.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  No tokens available.{" "}
                  <a href="/dashboard/settings/api" className="text-primary hover:underline">
                    Create one first
                  </a>
                </p>
              )}
            </div>

            {/* Setup Steps */}
            <div className="space-y-3">
              <Label>Setup Instructions</Label>
              <div className="space-y-3">
                {setupSteps.map((step, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                      {index + 1}
                    </div>
                    <p className="text-sm leading-relaxed">{step}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Configuration */}
            {client.configTemplate && (
              <div className="space-y-2">
                <Label>Configuration</Label>
                <div className="relative">
                  <pre className="p-4 rounded-lg bg-muted text-xs overflow-x-auto">
                    <code>
                      {client.configTemplate(
                        `${getMcpBaseUrl()}/mcp/${workspaceId}/sse`,
                        'YOUR_MCP_TOKEN_VALUE'
                      )}
                    </code>
                  </pre>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="absolute top-2 right-2"
                    onClick={() => handleCopy(
                      client.configTemplate!(
                        `${getMcpBaseUrl()}/mcp/${workspaceId}/sse`,
                        'YOUR_MCP_TOKEN_VALUE'
                      ),
                      'config'
                    )}
                  >
                    {copiedItem === 'config' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="code" className="space-y-6 mt-6">
            {/* Language Selector */}
            <div className="space-y-2">
              <Label>Select Language/Framework</Label>
              <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {defaultCodeExamples.map(ex => (
                    <SelectItem key={ex.language} value={ex.language}>
                      {ex.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Code Example */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Example Code</Label>
                <Badge variant="outline">{selectedExample.label}</Badge>
              </div>
              <div className="relative">
                <pre className="p-4 rounded-lg bg-muted text-xs overflow-x-auto">
                  <code>
                    {selectedExample.code(
                      `${getMcpBaseUrl()}/mcp/${workspaceId}/sse`,
                      'YOUR_MCP_TOKEN_VALUE'
                    )}
                  </code>
                </pre>
                <Button
                  size="sm"
                  variant="ghost"
                  className="absolute top-2 right-2"
                  onClick={() => handleCopy(
                    selectedExample.code(
                      `${getMcpBaseUrl()}/mcp/${workspaceId}/sse`,
                      'YOUR_MCP_TOKEN_VALUE'
                    ),
                    'code'
                  )}
                >
                  {copiedItem === 'code' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            {/* Quick Test */}
            <div className="rounded-lg bg-muted/50 p-4 space-y-2">
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4" />
                <span className="font-medium text-sm">Quick Test</span>
              </div>
              <p className="text-xs text-muted-foreground">
                After setting up, you can test your connection by listing available tools:
              </p>
              <pre className="p-2 rounded bg-background text-xs">
                <code>client.listTools() // or equivalent in your language</code>
              </pre>
            </div>
          </TabsContent>

          <TabsContent value="docs" className="space-y-6 mt-6">
            <div className="space-y-4">
              <div className="rounded-lg bg-muted/50 p-4">
                <h4 className="font-medium mb-2">MCP Protocol Overview</h4>
                <p className="text-sm text-muted-foreground">
                  The Model Context Protocol (MCP) is an open standard for connecting AI assistants to external tools and data sources. 
                  ProtoBox provides a secure MCP server that bridges your custom actions and workflows to any MCP-compatible client.
                </p>
              </div>

              <div className="space-y-3">
                <h4 className="font-medium">Key Features</h4>
                <ul className="space-y-2">
                  <li className="flex items-start gap-2 text-sm">
                    <ChevronRight className="h-4 w-4 mt-0.5 text-muted-foreground" />
                    <span><strong>Server-Sent Events (SSE)</strong> for real-time communication</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm">
                    <ChevronRight className="h-4 w-4 mt-0.5 text-muted-foreground" />
                    <span><strong>Token Authentication</strong> for secure access control</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm">
                    <ChevronRight className="h-4 w-4 mt-0.5 text-muted-foreground" />
                    <span><strong>Tool Discovery</strong> to automatically list available actions</span>
                  </li>
                  <li className="flex items-start gap-2 text-sm">
                    <ChevronRight className="h-4 w-4 mt-0.5 text-muted-foreground" />
                    <span><strong>Schema Validation</strong> for reliable tool execution</span>
                  </li>
                </ul>
              </div>

              {client.documentation && (
                <div className="space-y-3">
                  <h4 className="font-medium">Additional Resources</h4>
                  <div className="prose prose-sm max-w-none text-muted-foreground">
                    {client.documentation}
                  </div>
                </div>
              )}

              <Separator />

              <div className="flex gap-4 text-sm">
                <a 
                  href="https://github.com/chanl-ai/protobox-python/blob/main/docs/MCP_ARCHITECTURE.md" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  ProtoBox MCP Documentation →
                </a>
                <a 
                  href="https://modelcontextprotocol.io" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  MCP Protocol Specification →
                </a>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}