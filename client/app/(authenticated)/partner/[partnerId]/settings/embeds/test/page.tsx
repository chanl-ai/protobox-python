"use client"

import { useState, useEffect, use } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  AlertCircle,
  Loader2,
  RefreshCw
} from "lucide-react"
import { ProtoBoxIntegrations } from "@/components/integrations/protobox-integrations"
import { toast, Toaster } from "sonner"

interface EmbedTestPageProps {
  params: Promise<{ partnerId: string }>
}

// Mock integration data for demo
const mockIntegrations = [
  {
    id: "1",
    type: "google_calendar",
    name: "Google Calendar",
    description: "Schedule meetings and manage events",
    is_connected: false,
    status: "disconnected" as const
  },
  {
    id: "2",
    type: "hubspot",
    name: "HubSpot",
    description: "CRM and marketing automation",
    is_connected: true,
    connected_at: "2024-01-15T10:00:00Z",
    status: "connected" as const
  },
  {
    id: "3",
    type: "slack",
    name: "Slack",
    description: "Team communication and notifications",
    is_connected: false,
    status: "disconnected" as const
  },
  {
    id: "4",
    type: "salesforce",
    name: "Salesforce",
    description: "Customer relationship management",
    is_connected: true,
    connected_at: "2024-01-10T14:30:00Z",
    status: "connected" as const
  }
]

export default function EmbedTestPage({ params }: EmbedTestPageProps) {
  const { partnerId } = use(params)
  const [selectedTab, setSelectedTab] = useState("demo")
  const [refreshKey, setRefreshKey] = useState(0)
  const [integrations, setIntegrations] = useState(mockIntegrations)
  const [loading, setLoading] = useState(false)
  const [isConnecting, setIsConnecting] = useState<string | null>(null)

  // Test configuration
  const testConfig = {
    partnerId: "test_partner",
    secretKey: "test_secret_key_456",
    partnerUserId: "user_123",
    apiUrl: "/api/partner",
    workspaceId: "688000d0543c2e11c71283c2"
  }

  const handleConnect = async (integrationType: string) => {
    try {
      setIsConnecting(integrationType)
      toast.info(`Opening ${integrationType} authorization...`)
      
      // Simulate OAuth flow
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // In production, this would:
      // 1. Call partner backend to get OAuth URL
      // 2. Open OAuth popup
      // 3. Wait for completion
      // 4. Refresh integration list
      
      // For demo, just update the state
      setIntegrations(prev => prev.map(integration => 
        integration.type === integrationType
          ? { ...integration, is_connected: true, connected_at: new Date().toISOString(), status: "connected" as const }
          : integration
      ))
      
      toast.success(`Successfully connected ${integrationType}!`)
    } catch (error) {
      toast.error(`Failed to connect ${integrationType}`)
    } finally {
      setIsConnecting(null)
    }
  }

  const handleDisconnect = async (integrationId: string) => {
    const integration = integrations.find(i => i.id === integrationId)
    const confirmDisconnect = window.confirm(
      `Are you sure you want to disconnect ${integration?.name}?`
    )
    
    if (confirmDisconnect) {
      try {
        setLoading(true)
        
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 500))
        
        setIntegrations(prev => prev.map(i => 
          i.id === integrationId
            ? { ...i, is_connected: false, connected_at: undefined, status: "disconnected" as const }
            : i
        ))
        
        toast.success('Integration disconnected')
      } catch (error) {
        toast.error('Failed to disconnect')
      } finally {
        setLoading(false)
      }
    }
  }

  const handleSettings = (integrationId: string) => {
    const integration = integrations.find(i => i.id === integrationId)
    toast.info(`Opening settings for ${integration?.name}...`)
    // In production, would open settings modal or navigate to settings page
  }

  const handleRefresh = async (integrationId: string) => {
    const integration = integrations.find(i => i.id === integrationId)
    try {
      toast.info(`Refreshing ${integration?.name}...`)
      await new Promise(resolve => setTimeout(resolve, 1000))
      toast.success('Integration refreshed')
    } catch (error) {
      toast.error('Refresh failed')
    }
  }

  const handleManualRefresh = () => {
    setRefreshKey(prev => prev + 1)
    // In production, would refresh from API
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Test Embed Locally</h1>
        <p className="text-muted-foreground">
          Test the embed functionality before deploying to production
        </p>
      </div>

      {/* Test Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Test Configuration</CardTitle>
          <CardDescription>
            Configuration used for testing the embed
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium">Partner ID:</span>
              <code className="ml-2 px-2 py-1 bg-muted rounded">{testConfig.partnerId}</code>
            </div>
            <div>
              <span className="font-medium">Test User ID:</span>
              <code className="ml-2 px-2 py-1 bg-muted rounded">{testConfig.partnerUserId}</code>
            </div>
            <div>
              <span className="font-medium">API URL:</span>
              <code className="ml-2 px-2 py-1 bg-muted rounded">{testConfig.apiUrl}</code>
            </div>
            <div>
              <span className="font-medium">Secret Key:</span>
              <code className="ml-2 px-2 py-1 bg-muted rounded">***_12345</code>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Test Methods */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList>
          <TabsTrigger value="demo">Demo Mode</TabsTrigger>
          <TabsTrigger value="production">Production Mode</TabsTrigger>
        </TabsList>

        <TabsContent value="demo" className="space-y-4">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Demo Mode</AlertTitle>
            <AlertDescription>
              Using mock data to demonstrate the embed functionality. OAuth flows are simulated.
            </AlertDescription>
          </Alert>
        </TabsContent>

        <TabsContent value="production" className="space-y-4">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Production Mode</AlertTitle>
            <AlertDescription>
              In production, the embed will connect to your backend API to handle OAuth flows securely.
            </AlertDescription>
          </Alert>
        </TabsContent>
      </Tabs>

      {/* Embed Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Integration Marketplace</span>
            <Button 
              variant="outline" 
              size="sm"
              onClick={handleManualRefresh}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </CardTitle>
          <CardDescription>
            This is how the embed will appear to your customers
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg p-6 bg-gradient-to-br from-blue-50 to-indigo-100" key={refreshKey}>
            {selectedTab === "demo" && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md text-sm text-yellow-800">
                <strong>Demo Mode:</strong> OAuth flows are simulated. In production, clicking "Connect" would open the actual OAuth provider's authorization page.
              </div>
            )}
            <ProtoBoxIntegrations
              integrations={integrations}
              loading={loading || isConnecting !== null}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              onSettings={handleSettings}
              onRefresh={handleRefresh}
              className="animate-in fade-in duration-500"
            />
          </div>
        </CardContent>
      </Card>

      {/* Embed Code Example */}
      <Card>
        <CardHeader>
          <CardTitle>Implementation Example</CardTitle>
          <CardDescription>
            How this would be implemented in your application
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="react">
            <TabsList>
              <TabsTrigger value="react">React</TabsTrigger>
              <TabsTrigger value="html">HTML</TabsTrigger>
            </TabsList>

            <TabsContent value="react">
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                <code>{`import { ProtoBoxEmbed } from '@protobox/embed-react'

function App() {
  return (
    <ProtoBoxEmbed
      partnerId="${testConfig.partnerId}"
      secretKey={process.env.PROTOBOX_SECRET}
      userId="${testConfig.partnerUserId}"
      theme="light"
      showSearch={true}
    />
  )
}`}</code>
              </pre>
            </TabsContent>

            <TabsContent value="html">
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                <code>{`<script src="https://unpkg.com/@protobox/embed-web"></script>
<protobox-embed
  partner-id="${testConfig.partnerId}"
  secret-key="YOUR_SECRET_KEY"
  user-id="${testConfig.partnerUserId}"
  theme="light"
  show-search>
</protobox-embed>`}</code>
              </pre>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      
      <Toaster 
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155'
          }
        }}
      />
    </div>
  )
}