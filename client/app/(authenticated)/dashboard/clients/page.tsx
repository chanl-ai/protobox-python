"use client"

import { useState, useEffect } from "react"
import { Copy, Check, Globe, Plug2, Terminal, Code2, Sparkles, TrendingUp, Zap, Key, Shield, Eye, EyeOff } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuthStore } from "@/lib/auth/stores/auth.store"
import { useToast } from "@/hooks/use-toast"
import { ClientCard } from "@/components/clients/client-card"
import { ClientDetailsDialog } from "@/components/clients/client-details-dialog"
import { ClaudeDesktopDialog } from "@/components/clients/claude-desktop-dialog"
import { MCPTokensTab } from "@/components/api-settings/mcp-tokens-tab"
import { OAuthClientsTab } from "@/components/api-settings/oauth-clients-tab"
import { protoboxClient } from "@/lib/api/protobox-client"

export default function ClientsPage() {
  const { currentWorkspace } = useAuthStore()
  const { toast } = useToast()
  const [copiedItem, setCopiedItem] = useState<string | null>(null)
  const [stats, setStats] = useState<WorkspaceStats | null>(null)
  const [selectedClient, setSelectedClient] = useState<any>(null)
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false)
  const [claudeDesktopDialogOpen, setClaudeDesktopDialogOpen] = useState(false)
  const [showAnalytics, setShowAnalytics] = useState(true)
  
  // WorkspaceLoadingGuard guarantees currentWorkspace exists
  const workspaceId = currentWorkspace!.id
  
  // Load stats when workspace is ready
  useEffect(() => {
    loadStats()
  }, [workspaceId])

  const loadStats = async () => {
    
    try {
      const response = await protoboxClient.getWorkspaceStats(workspaceId)
      if (response.data) {
        setStats(response.data)
      } else if (response.error) {
        throw new Error(response.error)
      }
    } catch (error) {
      console.error("Failed to load stats:", error)
      // Fallback to individual counts if stats API not available
      try {
        const tokenResponse = await protoboxClient.getTokenCount(workspaceId)
        if (tokenResponse.data) {
          setStats({
            mcp_tokens_count: tokenResponse.data.total_tokens,
            oauth_clients_count: 0,
            actions_count: 0,
            integrations_count: 0,
            knowledge_docs_count: 0,
          })
        }
      } catch (fallbackError) {
        console.error("Failed to load fallback stats:", fallbackError)
      }
    }
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

  const handleViewDetails = (client: any) => {
    // Use specific dialogs for specific clients
    if (client.title === "Claude Desktop") {
      setClaudeDesktopDialogOpen(true)
    } else {
      setSelectedClient(client)
      setDetailsDialogOpen(true)
    }
  }

  // Client configurations with detailed setup information
  const clients = [
    {
      title: "Claude",
      description: "Connect Claude (Desktop, Web, CLI) using OAuth authentication for seamless MCP integration.",
      icon: "/images/claude-logo.svg",
      supportsOAuth: true,
      redirectUris: ["claude://oauth/callback", "http://localhost:8080/auth/callback", "https://claude.ai/api/auth/callback/mcp"],
      clientType: "public",
      setupSteps: [
        "Create OAuth client or select existing one",
        "Configure Claude with the OAuth client details",
        "Authorize access when prompted",
        "Start using your MCP tools in Claude"
      ],
      configTemplate: (url: string, token: string) => JSON.stringify({
        "mcpServers": {
          "protobox": {
            "url": url,
            "token": token
          }
        }
      }, null, 2),
      oauthConfigTemplate: (serverUrl: string, clientId: string) => JSON.stringify({
        "mcpServers": {
          "protobox": {
            "url": serverUrl,
            "oauth": {
              "clientId": clientId,
              "authorizationEndpoint": `${serverUrl}/authorize`,
              "tokenEndpoint": `${serverUrl}/token`,
              "scopes": ["mcp:read", "mcp:execute"]
            }
          }
        }
      }, null, 2),
      requirements: [
        "Claude account (Desktop, Web, or CLI)",
        "OAuth client configured for secure authentication",
        "Internet connection for OAuth flow"
      ],
      documentation: "Claude supports MCP servers through OAuth 2.1 authentication across all platforms (Desktop, Web, CLI). OAuth provides secure, seamless authentication without manual token management."
    },
    {
      title: "ChatGPT",
      description: "Connect ChatGPT to your MCP server using OAuth or OpenAI SDK with tokens.",
      icon: "/images/chatgpt-logo.svg",
      supportsOAuth: true,
      redirectUris: ["https://chat.openai.com/api/auth/callback", "https://chatgpt.com/auth/callback"],
      clientType: "confidential",
      setupSteps: [
        "Choose OAuth (recommended) or SDK method",
        "For OAuth: Configure MCP connection in ChatGPT",
        "For SDK: Install OpenAI SDK and use token authentication",
        "Test the connection with your tools"
      ],
      oauthConfigTemplate: (serverUrl: string, clientId: string) => `# ChatGPT MCP OAuth Configuration
MCP Server URL: ${serverUrl}
Client ID: ${clientId}
Authorization Endpoint: ${serverUrl}/authorize
Token Endpoint: ${serverUrl}/token
Scopes: mcp:read, mcp:execute

# Instructions:
1. In ChatGPT, go to Settings → Features → Model Context Protocol
2. Add new MCP server with the above details
3. Authorize access when prompted`,
      codeExamples: [
        {
          language: "python",
          label: "Python (OpenAI SDK)",
          code: (url: string, token: string) => `from openai import OpenAI

# Option 1: OAuth (recommended) - configure in ChatGPT UI
# Option 2: Direct API access with token
client = OpenAI(
    base_url="${url.replace('/mcp/', '/openai/v1/')}",
    api_key="${token}"
)

# Use your MCP tools via ChatGPT API
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Use my ProtoBox tools"}]
)`
        },
        {
          language: "javascript",
          label: "JavaScript/Node.js (OpenAI SDK)",
          code: (url: string, token: string) => `import OpenAI from 'openai';

// Option 1: OAuth (recommended) - configure in ChatGPT UI
// Option 2: Direct API access with token
const openai = new OpenAI({
  baseURL: '${url.replace('/mcp/', '/openai/v1/')}',
  apiKey: '${token}',
});

// Use your MCP tools via ChatGPT API
const response = await openai.chat.completions.create({
  model: 'gpt-4',
  messages: [{ role: 'user', content: 'Use my ProtoBox tools' }],
});`
        }
      ],
      requirements: [
        "ChatGPT Plus subscription for MCP features (OAuth method)",
        "OR OpenAI SDK installed for API method",
        "OAuth client configured (recommended) or MCP token"
      ],
      documentation: "ChatGPT supports MCP servers through OAuth (recommended) or via the OpenAI SDK with token authentication. OAuth provides seamless integration directly in the ChatGPT interface."
    },
    {
      title: "Cursor IDE",
      description: "AI-powered code editor with built-in MCP support. OAuth recommended for seamless setup.",
      icon: "/images/cursor-logo.svg",
      supportsOAuth: true,
      redirectUris: ["cursor://oauth/callback", "http://localhost:42424/auth/callback"],
      clientType: "public",
      setupSteps: [
        "Create OAuth client (Step 1 below)",
        "Open Cursor settings (Cmd+, or Ctrl+,)",
        "Search for 'MCP' in the settings",
        "Click 'Edit in settings.json'",
        "Add the ProtoBox server configuration (just URL, no token)",
        "Restart Cursor - it will auto-detect OAuth and prompt for authorization"
      ],
      configTemplate: (url: string, token: string) => JSON.stringify({
        "mcpServers": {
            "protobox": {
              "url": url,
              "token": token
          }
        }
      }, null, 2),
      oauthConfigTemplate: (serverUrl: string, clientId: string) => {
        // For OAuth, use the workspace-specific SSE endpoint
        return JSON.stringify({
          "mcpServers": {
            "protobox": {
              "url": serverUrl
            }
          }
        }, null, 2)
      },
      requirements: [
        "Cursor IDE installed",
        "OAuth client configured (recommended) or MCP token"
      ],
      documentation: "Cursor has native MCP support with automatic OAuth discovery. Simply provide the server URL and Cursor will auto-detect OAuth endpoints and handle the authentication flow."
    },
    {
      title: "FastMCP Client",
      description: "Build client applications with a controlled, programmatic interface. Native OAuth support.",
      icon: <Code2 className="h-5 w-5" />,
      supportsOAuth: true,
      redirectUris: ["http://localhost:8765/callback", "http://localhost:3000/callback"],
      clientType: "public",
      setupSteps: [
        "Install FastMCP client library",
        "Initialize the client with OAuth configuration",
        "Connect to the ProtoBox server",
        "Use the client API to interact with your tools"
      ],
      codeExamples: [
        {
          language: "javascript",
          label: "JavaScript/TypeScript (OAuth)",
          code: (url: string, token: string) => `import { FastMCP } from '@fastmcp/client';

// OAuth configuration (recommended)
const mcp = new FastMCP({
  serverUrl: '${url}',
  oauth: {
    clientId: 'YOUR_CLIENT_ID',
    authorizationEndpoint: '${url}/authorize',
    tokenEndpoint: '${url}/token',
    scopes: ['mcp:read', 'mcp:execute']
  }
});

// Connect and use your tools
await mcp.connect();
const tools = await mcp.listTools();

// Execute a tool
const result = await mcp.executeTool('your-tool-name', {
  // tool parameters
});`
        },
        {
          language: "javascript",
          label: "JavaScript/TypeScript (Token)",
          code: (url: string, token: string) => `import { FastMCP } from '@fastmcp/client';

// Token-based authentication (legacy)
const mcp = new FastMCP({
  url: '${url}',
  token: '${token}'
});

// Connect and use your tools
await mcp.connect();
const tools = await mcp.listTools();`
        }
      ],
      oauthConfigTemplate: (serverUrl: string, clientId: string) => `# FastMCP OAuth Configuration
export const mcpConfig = {
  serverUrl: "${serverUrl}",
  oauth: {
    clientId: "${clientId}",
    authorizationEndpoint: "${serverUrl}/authorize",
    tokenEndpoint: "${serverUrl}/token",
    scopes: ["mcp:read", "mcp:execute"]
  }
};`,
      requirements: [
        "Node.js or browser environment",
        "npm install @fastmcp/client",
        "OAuth client configured (recommended) or MCP token"
      ],
      documentation: "FastMCP provides a high-performance client library with native OAuth 2.1 support for secure authentication with MCP servers."
    },
    {
      title: "Terminal (via MCP CLI)",
      description: "Access your MCP tools from the command line with the official MCP CLI.",
      icon: <Terminal className="h-5 w-5" />,
      setupSteps: [
        "Install the MCP CLI globally",
        "Configure your ProtoBox connection",
        "Use CLI commands to interact with tools",
        "Optionally save configuration for future use"
      ],
      configTemplate: (url: string, token: string) => `# Connect to ProtoBox MCP server
mcp connect ${url} --token ${token}

# List available tools
mcp tools list

# Execute a specific tool
mcp exec <tool-name> --params '{"key": "value"}'

# Save configuration for future use
mcp config save protobox --url ${url} --token ${token}`,
      requirements: [
        "Node.js installed",
        "npm install -g @mcp/cli",
        "Valid MCP token from ProtoBox"
      ],
      documentation: "The MCP CLI provides a command-line interface for interacting with any MCP server, including ProtoBox."
    },
    {
      title: "Custom Integration",
      description: "Connect custom tools, or third-party MCP clients using OAuth or tokens.",
      icon: <Sparkles className="h-5 w-5" />,
      supportsOAuth: true,
      redirectUris: ["https://yourapp.com/auth/callback", "https://yourapp.vercel.app/auth/callback"],
      clientType: "public",
      setupSteps: [
        "Choose OAuth (recommended) or token authentication",
        "For OAuth: Create client and test with MCP Inspector",
        "For tokens: Use direct SSE connection with Bearer auth",
        "Test connection and explore available tools"
      ],
      configTemplate: (url: string, token: string) => `# Token-based Authentication
SSE Endpoint: ${url}
Token: ${token}
Protocol: MCP over Server-Sent Events (SSE)
Authentication: Bearer token in Authorization header

Example connection:
Headers: {
  "Authorization": "Bearer ${token}",
  "Accept": "text/event-stream"
}

# cURL example:
curl -H "Authorization: Bearer ${token}" \\
     -H "Accept: text/event-stream" \\
     "${url}"`,
      oauthConfigTemplate: (serverUrl: string, clientId: string) => {
        // For OAuth, use the generic /mcp endpoint (not workspace-specific)
        const oauthServerUrl = serverUrl.replace(/\/mcp\/[^\/]+\/sse$/, '/mcp')
        const baseUrl = serverUrl.replace(/\/mcp.*$/, '')
        
        return `# OAuth Configuration for MCP Inspector
Server URL: ${oauthServerUrl}
Client ID: ${clientId}

# OAuth Discovery Endpoints:
Discovery: ${baseUrl}/.well-known/oauth-authorization-server
Authorization: ${baseUrl}/authorize
Token: ${baseUrl}/token

# MCP Inspector Setup:
1. Open MCP Inspector (https://mcp-inspector.modelcontextprotocol.io)
2. Add new server connection
3. Choose "OAuth 2.0" authentication
4. Server URL: ${oauthServerUrl}
5. Client ID: ${clientId}
6. It will auto-discover endpoints and guide you through authorization

# Custom Implementation:
const config = {
  serverUrl: "${oauthServerUrl}",
  oauth: {
    clientId: "${clientId}",
    authorizationEndpoint: "${baseUrl}/authorize",
    tokenEndpoint: "${baseUrl}/token",
    scopes: ["mcp:read", "mcp:execute", "mcp:write"]
  }
};`
      },
      codeExamples: [
        {
          language: "javascript",
          label: "OAuth Client (Recommended)",
          code: (url: string, token: string) => `// OAuth-based MCP client
import { MCPClient } from '@mcp/sdk';

const client = new MCPClient({
  serverUrl: '${url}',
  auth: {
    type: 'oauth',
    discoveryUrl: '${url.replace('/mcp/', '/')}/.well-known/oauth-authorization-server',
    clientId: 'YOUR_CLIENT_ID', // From OAuth setup
    scopes: ['mcp:read', 'mcp:execute']
  }
});

await client.connect();
const tools = await client.listTools();`
        },
        {
          language: "javascript", 
          label: "Token-based (Legacy)",
          code: (url: string, token: string) => `// Token-based MCP client  
const eventSource = new EventSource('${url}', {
  headers: {
    'Authorization': 'Bearer ${token}'
  }
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle incoming MCP messages
};`
        },
        {
          language: "python",
          label: "Python OAuth Client",
          code: (url: string, token: string) => `# Python OAuth MCP client
import httpx
from mcp_client import MCPClient

client = MCPClient(
    server_url="${url}",
    oauth_config={
        "client_id": "YOUR_CLIENT_ID",
        "authorization_endpoint": "${url.replace('/mcp/', '/')}/authorize", 
        "token_endpoint": "${url.replace('/mcp/', '/')}/token",
        "scopes": ["mcp:read", "mcp:execute"]
    }
)

await client.connect()
tools = await client.list_tools()`
        }
      ],
      requirements: [
        "MCP-compatible client (MCP Inspector, FastMCP, etc.)",
        "OAuth client configured (recommended) or MCP token",
        "Understanding of MCP protocol for custom implementations"
      ],
      documentation: "For custom integrations, OAuth provides the most secure and standard way to authenticate. MCP Inspector and most modern MCP clients support OAuth discovery. For legacy integrations, direct token authentication is still supported."
    }
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-3">
          <Plug2 className="h-8 w-8 text-muted-foreground" />
          <div>
            <h1 className="text-3xl font-bold">MCP Clients</h1>
            <p className="text-muted-foreground">Connect your MCP server to different AI assistants and tools</p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowAnalytics(!showAnalytics)}
        >
          {showAnalytics ? (
            <><EyeOff className="h-4 w-4 mr-2" /> Hide Analytics</>
          ) : (
            <><Eye className="h-4 w-4 mr-2" /> Show Analytics</>
          )}
        </Button>
      </div>

      {/* Stats Cards */}
      {showAnalytics && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Active Connections</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">3</div>
              <p className="text-xs text-muted-foreground mt-1">
                <TrendingUp className="inline h-3 w-3 text-green-500 mr-1" />
                2 new this week
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Requests Today</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">1,234</div>
              <p className="text-xs text-muted-foreground mt-1">
                Across all clients
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Most Active Client</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">Claude</div>
              <p className="text-xs text-muted-foreground mt-1">
                234 requests today
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Available Tokens</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.mcp_tokens_count || 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Active MCP tokens
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* MCP Endpoint Section */}
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                MCP Endpoint
              </CardTitle>
              <CardDescription>
                Your workspace MCP endpoint for connecting AI assistants and tools
              </CardDescription>
            </div>
            <Badge variant="outline" className="ml-auto">
              Workspace: {currentWorkspace!.name}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Input
                value={`${getMcpBaseUrl()}/mcp/${workspaceId}/sse`}
                readOnly
                className="font-mono text-sm"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleCopy(`${getMcpBaseUrl()}/mcp/${workspaceId}/sse`, 'mcp-url')}
              >
                {copiedItem === 'mcp-url' ? (
                  <Check className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              This URL requires an MCP token for authentication. Create tokens in the Tokens tab below.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Tabs Section */}
      <div>
        <Tabs defaultValue="connect-clients" className="">
          <TabsList className="">
            <TabsTrigger value="connect-clients">
              <Plug2 className="h-4 w-4 mr-2" />
              Connect Your Clients
            </TabsTrigger>
            <TabsTrigger value="tokens">
              <Code2 className="h-4 w-4 mr-2" />
              Tokens
            </TabsTrigger>
            <TabsTrigger value="oauth">
              <Shield className="h-4 w-4 mr-2" />
              OAuth
            </TabsTrigger>
            <TabsTrigger value="api-keys">
              <Key className="h-4 w-4 mr-2" />
              API Keys
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="connect-clients" className="mt-6 space-y-4">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-semibold">Available Clients</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Choose from various AI assistants and tools that support the MCP protocol.
                </p>
              </div>
            </div>
            <div className="grid gap-4 grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
              {clients.map((client, index) => (
                <ClientCard 
                  key={index} 
                  {...client} 
                  onViewDetails={() => handleViewDetails(client)}
                />
              ))}
            </div>
          </TabsContent>
            
          <TabsContent value="tokens" className="mt-6">
              <MCPTokensTab workspaceId={currentWorkspace!.id} />
            </TabsContent>
            
          <TabsContent value="oauth" className="mt-6">
              <OAuthClientsTab workspaceId={currentWorkspace!.id} />
            </TabsContent>
            
          <TabsContent value="api-keys" className="space-y-4 mt-6">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-semibold">API Keys</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    Long-lived API keys for programmatic access to your workspace.
                  </p>
                </div>
              </div>
              
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center py-8">
                    <Key className="mx-auto h-12 w-12 text-muted-foreground opacity-50" />
                    <h4 className="mt-4 text-sm font-semibold">API Keys (Coming Soon)</h4>
                    <p className="mt-2 text-sm text-muted-foreground">
                      API keys for programmatic access will be available in a future update.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>


      {/* Help Section */}
      <div className="mt-8 text-center">
        <p className="text-sm text-muted-foreground">
          Don't see your client?{" "}
          <a 
            href="https://github.com/chanl-ai/protobox-python/tree/main/docs" 
            target="_blank" 
            rel="noopener noreferrer" 
            className="text-primary hover:underline"
          >
            Check our documentation
          </a>
          {" "}or{" "}
          <a 
            href="https://github.com/chanl-ai/protobox-python/issues" 
            className="text-primary hover:underline"
          >
            contact support
          </a>
        </p>
      </div>

      {/* Client Details Dialog */}
      {selectedClient && (
        <ClientDetailsDialog
          open={detailsDialogOpen}
          onOpenChange={setDetailsDialogOpen}
          client={selectedClient}
        />
      )}
      
      {/* Claude Desktop Dialog */}
      <ClaudeDesktopDialog
        open={claudeDesktopDialogOpen}
        onOpenChange={setClaudeDesktopDialogOpen}
      />
    </div>
  )
}