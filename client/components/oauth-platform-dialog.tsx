"use client"

import { useState, useEffect } from "react"
import { Copy, Check, Plus, Trash2, Shield, Globe, RefreshCw, AlertCircle, ExternalLink, Sparkles, Bot, Code2, Settings2 } from "lucide-react"
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
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"

interface OAuthPlatformDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  workspaceId: string
}

interface PlatformClient {
  platform: 'claude' | 'chatgpt' | 'cursor' | 'custom'
  client?: MCPOAuthClient
  credentials?: CreateOAuthClientResponse
}

export function OAuthPlatformDialog({ open, onOpenChange, workspaceId }: OAuthPlatformDialogProps) {
  const { toast } = useToast()
  const [platformClients, setPlatformClients] = useState<PlatformClient[]>([])
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState<string | null>(null)
  const [copiedItem, setCopiedItem] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState("claude")
  
  // Custom client form state
  const [clientName, setClientName] = useState("")
  const [clientDescription, setClientDescription] = useState("")
  const [redirectUris, setRedirectUris] = useState<string[]>(["http://localhost:3000/callback"])

  useEffect(() => {
    if (open && workspaceId) {
      loadPlatformClients()
    }
  }, [open, workspaceId])

  const loadPlatformClients = async () => {
    setLoading(true)
    try {
      const data = await mcpOAuthApi.listClients()
      
      // Group clients by platform based on name/description
      const platforms: PlatformClient[] = [
        {
          platform: 'claude',
          client: data.find(c => c.client_name.toLowerCase().includes('claude'))
        },
        {
          platform: 'chatgpt',
          client: data.find(c => c.client_name.toLowerCase().includes('chatgpt') || c.client_name.toLowerCase().includes('openai'))
        },
        {
          platform: 'cursor',
          client: data.find(c => c.client_name.toLowerCase().includes('cursor'))
        }
      ]
      
      setPlatformClients(platforms)
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

  const createPlatformClient = async (platform: 'claude' | 'chatgpt' | 'cursor') => {
    setCreating(platform)
    
    // Platform-specific configurations
    const configs = {
      claude: {
        client_name: "Claude Custom Connector",
        description: "OAuth client for Claude.ai custom connector integration",
        redirect_uris: ["https://claude.ai/api/auth/callback/custom"],
        scopes: ["mcp:read", "mcp:write", "mcp:execute"],
        token_endpoint_auth_method: "client_secret_basic",
        client_type: "confidential"
      },
      chatgpt: {
        client_name: "ChatGPT GPT Action",
        description: "OAuth client for ChatGPT GPT Actions integration",
        redirect_uris: ["https://chat.openai.com/aip/g/callback"],
        scopes: ["mcp:read", "mcp:execute"],
        token_endpoint_auth_method: "client_secret_post",
        client_type: "confidential"
      },
      cursor: {
        client_name: "Cursor IDE Integration",
        description: "OAuth client for Cursor IDE MCP integration",
        redirect_uris: ["http://localhost:42424/callback"],
        scopes: ["mcp:read", "mcp:write", "mcp:execute", "offline_access"],
        token_endpoint_auth_method: "none",
        client_type: "public"
      }
    }
    
    try {
      const config = configs[platform]
      const response = await mcpOAuthApi.createClient(config)
      
      // Update platform clients with new credentials
      setPlatformClients(prev => prev.map(p => 
        p.platform === platform 
          ? { ...p, credentials: response, client: { ...response, ...config } as any }
          : p
      ))
      
      toast({
        title: `${platform.charAt(0).toUpperCase() + platform.slice(1)} client created!`,
        description: "Save the credentials now - the secret won't be shown again",
      })
    } catch (error) {
      toast({
        title: "Failed to create OAuth client",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      })
    } finally {
      setCreating(null)
    }
  }

  const revokePlatformClient = async (platform: string, clientId: string) => {
    try {
      await mcpOAuthApi.revokeClient(clientId)
      await loadPlatformClients()
      toast({
        title: "Client revoked",
        description: `${platform} OAuth client has been revoked`,
      })
    } catch (error) {
      toast({
        title: "Failed to revoke client",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      })
    }
  }

  const getBaseUrl = () => {
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL
    }
    return process.env.NODE_ENV === 'development' 
      ? 'http://localhost:8090'
      : 'http://localhost:8090'
  }

  const ClaudeTab = () => {
    const claudeClient = platformClients.find(p => p.platform === 'claude')
    
    return (
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-orange-500" />
              Claude Custom Connector
            </h3>
            <p className="text-sm text-muted-foreground">
              Connect your MCP server to Claude.ai using a secure OAuth connection
            </p>
          </div>
        </div>

        {claudeClient?.credentials ? (
          <Alert className="border-green-500/50 bg-green-50/10">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="space-y-3">
              <p className="font-semibold">Claude client ready! Follow these steps to connect:</p>
              
              <div className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label className="text-xs">Client ID</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      value={claudeClient.credentials.client_id}
                      readOnly
                      className="font-mono text-xs"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleCopy(claudeClient.credentials!.client_id, 'claude-client-id')}
                    >
                      {copiedItem === 'claude-client-id' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label className="text-xs">Client Secret</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      value={claudeClient.credentials.client_secret}
                      readOnly
                      className="font-mono text-xs"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleCopy(claudeClient.credentials!.client_secret, 'claude-client-secret')}
                    >
                      {copiedItem === 'claude-client-secret' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              </div>
            </AlertDescription>
          </Alert>
        ) : claudeClient?.client ? (
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="default">Active</Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-destructive"
                    onClick={() => revokePlatformClient('Claude', claudeClient.client.client_id)}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Revoke
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">
                  Client ID: <code className="text-xs">{claudeClient.client.client_id.substring(0, 20)}...</code>
                </p>
                <Alert>
                  <AlertDescription className="text-xs">
                    To get your client secret, revoke this client and create a new one.
                  </AlertDescription>
                </Alert>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-4">
                <Sparkles className="mx-auto h-12 w-12 text-orange-500 opacity-50" />
                <div className="space-y-2">
                  <h4 className="font-semibold">No Claude client configured</h4>
                  <p className="text-sm text-muted-foreground">
                    Generate OAuth credentials to connect Claude to your MCP server
                  </p>
                </div>
                <Button
                  onClick={() => createPlatformClient('claude')}
                  disabled={creating === 'claude'}
                >
                  {creating === 'claude' ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Generate Claude Credentials
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <Separator />

        <div className="space-y-3">
          <h4 className="font-semibold">Setup Instructions</h4>
          <ol className="list-decimal list-inside space-y-2 text-sm">
            <li>Generate credentials using the button above</li>
            <li>Go to Claude.ai → Settings → Custom Connectors</li>
            <li>Click "Add Custom Connector"</li>
            <li>Configure with these settings:</li>
          </ol>
          
          <Card className="bg-muted/50">
            <CardContent className="pt-4 space-y-2 text-sm">
              <div><strong>Name:</strong> ProtoBox MCP</div>
              <div><strong>Authorization URL:</strong> <code className="text-xs">{getBaseUrl()}/authorize</code></div>
              <div><strong>Token URL:</strong> <code className="text-xs">{getBaseUrl()}/token</code></div>
              <div><strong>Scope:</strong> <code className="text-xs">mcp:read mcp:write mcp:execute</code></div>
              <div><strong>Base API URL:</strong> <code className="text-xs">{getBaseUrl()}/mcp</code></div>
            </CardContent>
          </Card>
          
          <p className="text-sm text-muted-foreground">
            5. Paste your Client ID and Client Secret from above
          </p>
          <p className="text-sm text-muted-foreground">
            6. Click "Connect" to authorize Claude to access your MCP server
          </p>
        </div>
      </div>
    )
  }

  const ChatGPTTab = () => {
    const chatgptClient = platformClients.find(p => p.platform === 'chatgpt')
    
    return (
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Bot className="h-5 w-5 text-green-500" />
              ChatGPT GPT Actions
            </h3>
            <p className="text-sm text-muted-foreground">
              Add MCP server capabilities to your ChatGPT custom GPT
            </p>
          </div>
        </div>

        {chatgptClient?.credentials ? (
          <Alert className="border-green-500/50 bg-green-50/10">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="space-y-3">
              <p className="font-semibold">ChatGPT client ready! Use these credentials in your GPT:</p>
              
              <div className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label className="text-xs">Client ID</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      value={chatgptClient.credentials.client_id}
                      readOnly
                      className="font-mono text-xs"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleCopy(chatgptClient.credentials!.client_id, 'chatgpt-client-id')}
                    >
                      {copiedItem === 'chatgpt-client-id' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label className="text-xs">Client Secret</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      value={chatgptClient.credentials.client_secret}
                      readOnly
                      className="font-mono text-xs"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleCopy(chatgptClient.credentials!.client_secret, 'chatgpt-client-secret')}
                    >
                      {copiedItem === 'chatgpt-client-secret' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              </div>
            </AlertDescription>
          </Alert>
        ) : chatgptClient?.client ? (
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="default">Active</Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-destructive"
                    onClick={() => revokePlatformClient('ChatGPT', chatgptClient.client.client_id)}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Revoke
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">
                  Client ID: <code className="text-xs">{chatgptClient.client.client_id.substring(0, 20)}...</code>
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-4">
                <Bot className="mx-auto h-12 w-12 text-green-500 opacity-50" />
                <div className="space-y-2">
                  <h4 className="font-semibold">No ChatGPT client configured</h4>
                  <p className="text-sm text-muted-foreground">
                    Generate OAuth credentials for your ChatGPT custom GPT
                  </p>
                </div>
                <Button
                  onClick={() => createPlatformClient('chatgpt')}
                  disabled={creating === 'chatgpt'}
                >
                  {creating === 'chatgpt' ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Generate ChatGPT Credentials
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <Separator />

        <div className="space-y-3">
          <h4 className="font-semibold">Setup Instructions</h4>
          <ol className="list-decimal list-inside space-y-2 text-sm">
            <li>Generate credentials using the button above</li>
            <li>Go to ChatGPT → Create GPT → Actions</li>
            <li>Set Authentication Type to "OAuth"</li>
            <li>Configure with these settings:</li>
          </ol>
          
          <Card className="bg-muted/50">
            <CardContent className="pt-4 space-y-2 text-sm">
              <div><strong>Authorization URL:</strong> <code className="text-xs">{getBaseUrl()}/authorize</code></div>
              <div><strong>Token URL:</strong> <code className="text-xs">{getBaseUrl()}/token</code></div>
              <div><strong>Scope:</strong> <code className="text-xs">mcp:read mcp:execute</code></div>
              <div><strong>Token Exchange Method:</strong> POST</div>
            </CardContent>
          </Card>
          
          <p className="text-sm text-muted-foreground">
            5. Add your Client ID and Client Secret from above
          </p>
          <p className="text-sm text-muted-foreground">
            6. Import the MCP OpenAPI schema to define available actions
          </p>
        </div>
      </div>
    )
  }

  const CursorTab = () => {
    const cursorClient = platformClients.find(p => p.platform === 'cursor')
    
    return (
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Code2 className="h-5 w-5 text-blue-500" />
              Cursor IDE
            </h3>
            <p className="text-sm text-muted-foreground">
              Connect Cursor IDE to your MCP server for AI-powered development
            </p>
          </div>
        </div>

        {cursorClient?.credentials ? (
          <Alert className="border-green-500/50 bg-green-50/10">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="space-y-3">
              <p className="font-semibold">Cursor client ready! Configure your IDE:</p>
              
              <div className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label className="text-xs">Client ID</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      value={cursorClient.credentials.client_id}
                      readOnly
                      className="font-mono text-xs"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleCopy(cursorClient.credentials!.client_id, 'cursor-client-id')}
                    >
                      {copiedItem === 'cursor-client-id' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              </div>
            </AlertDescription>
          </Alert>
        ) : cursorClient?.client ? (
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="default">Active</Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-destructive"
                    onClick={() => revokePlatformClient('Cursor', cursorClient.client.client_id)}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Revoke
                  </Button>
                </div>
                <p className="text-sm text-muted-foreground">
                  Client ID: <code className="text-xs">{cursorClient.client.client_id.substring(0, 20)}...</code>
                </p>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-4">
                <Code2 className="mx-auto h-12 w-12 text-blue-500 opacity-50" />
                <div className="space-y-2">
                  <h4 className="font-semibold">No Cursor client configured</h4>
                  <p className="text-sm text-muted-foreground">
                    Generate OAuth credentials for Cursor IDE integration
                  </p>
                </div>
                <Button
                  onClick={() => createPlatformClient('cursor')}
                  disabled={creating === 'cursor'}
                >
                  {creating === 'cursor' ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Generate Cursor Credentials
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <Separator />

        <div className="space-y-3">
          <h4 className="font-semibold">Setup Instructions</h4>
          <ol className="list-decimal list-inside space-y-2 text-sm">
            <li>Generate credentials using the button above</li>
            <li>Open Cursor Settings → MCP Servers</li>
            <li>Add a new MCP server with these settings:</li>
          </ol>
          
          <Card className="bg-muted/50">
            <CardContent className="pt-4 space-y-2 text-sm">
              <div><strong>Server URL:</strong> <code className="text-xs">{getBaseUrl()}/mcp</code></div>
              <div><strong>Auth Type:</strong> OAuth 2.0 (PKCE)</div>
              <div><strong>Authorization URL:</strong> <code className="text-xs">{getBaseUrl()}/authorize</code></div>
              <div><strong>Token URL:</strong> <code className="text-xs">{getBaseUrl()}/token</code></div>
              <div><strong>Scope:</strong> <code className="text-xs">mcp:read mcp:write mcp:execute offline_access</code></div>
            </CardContent>
          </Card>
          
          <p className="text-sm text-muted-foreground">
            4. Enter the Client ID from above
          </p>
          <p className="text-sm text-muted-foreground">
            5. Click "Connect" to authorize Cursor
          </p>
        </div>
      </div>
    )
  }

  const CustomTab = () => {
    return (
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Settings2 className="h-5 w-5" />
              Custom OAuth Client
            </h3>
            <p className="text-sm text-muted-foreground">
              Create a custom OAuth client for your own integration
            </p>
          </div>
        </div>

        <Card>
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <Settings2 className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
              <div className="space-y-2">
                <h4 className="font-semibold">Advanced OAuth Configuration</h4>
                <p className="text-sm text-muted-foreground">
                  For custom integrations, use the original OAuth client manager
                </p>
              </div>
              <Button
                variant="outline"
                onClick={() => {
                  onOpenChange(false)
                  // This would trigger opening the original OAuth dialog
                  // You'd need to implement this communication in the parent component
                }}
              >
                <Settings2 className="h-4 w-4 mr-2" />
                Open Advanced OAuth Manager
              </Button>
            </div>
          </CardContent>
        </Card>

        <Alert>
          <Shield className="h-4 w-4" />
          <AlertDescription>
            <strong>OAuth 2.1 Server Endpoints:</strong>
            <div className="mt-2 space-y-1 text-xs">
              <div>Discovery: <code>{getBaseUrl()}/.well-known/oauth-authorization-server</code></div>
              <div>Register: <code>{getBaseUrl()}/register</code></div>
              <div>Authorize: <code>{getBaseUrl()}/authorize</code></div>
              <div>Token: <code>{getBaseUrl()}/token</code></div>
            </div>
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            AI Assistant OAuth Setup
          </DialogTitle>
          <DialogDescription>
            Generate OAuth credentials for connecting AI assistants to your MCP server
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="claude" className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              Claude
            </TabsTrigger>
            <TabsTrigger value="chatgpt" className="flex items-center gap-2">
              <Bot className="h-4 w-4" />
              ChatGPT
            </TabsTrigger>
            <TabsTrigger value="cursor" className="flex items-center gap-2">
              <Code2 className="h-4 w-4" />
              Cursor
            </TabsTrigger>
            <TabsTrigger value="custom" className="flex items-center gap-2">
              <Settings2 className="h-4 w-4" />
              Custom
            </TabsTrigger>
          </TabsList>

          <TabsContent value="claude" className="mt-4">
            <ClaudeTab />
          </TabsContent>

          <TabsContent value="chatgpt" className="mt-4">
            <ChatGPTTab />
          </TabsContent>

          <TabsContent value="cursor" className="mt-4">
            <CursorTab />
          </TabsContent>

          <TabsContent value="custom" className="mt-4">
            <CustomTab />
          </TabsContent>
        </Tabs>

        <DialogFooter className="flex justify-between items-center">
          <Button variant="link" className="text-xs p-0 h-auto" asChild>
            <a href="https://github.com/chanl-ai/protobox-python/blob/main/docs/OAUTH_IMPLEMENTATION.md" target="_blank" rel="noopener noreferrer">
              View OAuth Documentation →
            </a>
          </Button>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Shield className="h-4 w-4" />
            <span>All clients are scoped to your workspace</span>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}