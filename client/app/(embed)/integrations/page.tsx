"use client"

import { useSearchParams } from "next/navigation"
import { useEffect, useState, Suspense } from "react"
import { ProtoBoxIntegrations } from "@/components/integrations/protobox-integrations"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { toast, Toaster } from "sonner"
import { ProtoBoxIframeClient } from "@/lib/protobox-embed/iframe-client"
import { PARENT_MESSAGES, Integration } from "@/lib/protobox-embed/message-types"
import { PartnerIntegrationFilter, getPartnerIntegrations } from "@/lib/partner-integrations"
import { createPartnerAPIClient, MockPartnerAPIClient, PartnerIntegration } from "@/lib/api/partner-api"

// Mock data for now - will be replaced with real API calls
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
    is_connected: false,
    status: "disconnected" as const
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
    is_connected: false,
    status: "disconnected" as const
  },
  {
    id: "5",
    type: "stripe",
    name: "Stripe",
    description: "Payment processing and subscriptions",
    is_connected: false,
    status: "disconnected" as const
  },
  {
    id: "6",
    type: "shopify",
    name: "Shopify",
    description: "E-commerce platform integration",
    is_connected: false,
    status: "disconnected" as const
  }
]

function IntegrationsContent() {
  const searchParams = useSearchParams()
  const partnerId = searchParams.get("partner_id")
  const userId = searchParams.get("user_id")
  const theme = searchParams.get("theme") || "light"
  const mode = searchParams.get("mode") || "auto" // demo, sandbox, production, auto
  const bgFrom = searchParams.get("bg_from")
  const bgTo = searchParams.get("bg_to")
  
  const [integrations, setIntegrations] = useState<typeof mockIntegrations>([])
  const [loading, setLoading] = useState(true)
  const [dataMode, setDataMode] = useState<"demo" | "sandbox" | "production">("demo")
  const [activeTab, setActiveTab] = useState("all")
  const [embedClient, setEmbedClient] = useState<ProtoBoxIframeClient | null>(null)
  const [partnerFilter, setPartnerFilter] = useState<PartnerIntegrationFilter | null>(null)
  const [apiClient, setApiClient] = useState<any>(null)
  const [isInitialized, setIsInitialized] = useState(false)

  // Initialize partner filter and API client
  useEffect(() => {
    if (partnerId && userId) {
      const filter = new PartnerIntegrationFilter(partnerId)
      setPartnerFilter(filter)
    }
  }, [partnerId, userId])

  // Determine data mode and load integrations
  useEffect(() => {
    const determineMode = async () => {
      if (!partnerId || !partnerFilter) return
      
      setLoading(true)
      
      try {
        let integrationsData = []
        let determinedMode = "demo"
        let client = null
        
        // Explicit mode parameter
        if (mode === "demo") {
          determinedMode = "demo"
        }
        // Demo partner IDs always use demo mode  
        else if (["demo_partner", "try_protobox", "test_partner", "test_partner_dev"].includes(partnerId)) {
          determinedMode = "demo"
        }
        // Sandbox mode
        else if (mode === "sandbox" || partnerId === "sandbox") {
          determinedMode = "sandbox"
        }
        // Production mode
        else {
          determinedMode = "production"
        }
        
        // Set the mode
        setDataMode(determinedMode as "production" | "demo" | "sandbox")
        
        // Create appropriate client
        if (determinedMode === "production") {
          client = createPartnerAPIClient(partnerId!, userId!)
        } else {
          client = new MockPartnerAPIClient(partnerId!, userId!)
        }
        setApiClient(client)
        
        // Load integrations based on mode
        if (determinedMode === "demo") {
          integrationsData = partnerFilter.filterIntegrations(mockIntegrations)
        } else {
          try {
            const response = await client.getAvailableIntegrations()
            if (response.data) {
              integrationsData = partnerFilter.filterIntegrations(response.data.map(mapAPIIntegration))
            } else {
              // Fall back to mock data
              integrationsData = partnerFilter.filterIntegrations(mockIntegrations)
            }
          } catch (error) {
            // Fall back to filtered mock data
            setDataMode("demo")
            integrationsData = partnerFilter.filterIntegrations(mockIntegrations)
          }
        }
        
        setIntegrations(integrationsData)
      } catch (error) {
        setIntegrations([])
      } finally {
        setLoading(false)
      }
    }
    
    determineMode()
  }, [partnerId, userId, mode, partnerFilter])
  
  // Helper function to map API response to our integration format
  const mapAPIIntegration = (apiIntegration: PartnerIntegration) => ({
    id: apiIntegration.id,
    type: apiIntegration.integration_type,
    name: apiIntegration.display_name,
    description: apiIntegration.description,
    category: apiIntegration.category,
    is_connected: apiIntegration.is_connected,
    connected_at: apiIntegration.connected_at,
    status: apiIntegration.status as "connected" | "disconnected" | "setup" | "error",
    permissions: apiIntegration.permissions
  })

  // Initialize iframe client
  useEffect(() => {
    if (!partnerId || !userId) return
    
    const client = new ProtoBoxIframeClient({
      partnerId,
      userId,
      debug: true,
      onMessage: (message) => {
      }
    })
    
    // Set up listeners
    client.on(PARENT_MESSAGES.UPDATE_THEME, (data) => {
      const theme = data?.theme || 'light'
      document.documentElement.classList.remove('light', 'dark')
      document.documentElement.classList.add(theme)
    })
    
    client.on(PARENT_MESSAGES.FILTER_INTEGRATIONS, (data) => {
      // Handle filtering
    })
    
    // Validate user access if using API client
    if (apiClient) {
      apiClient.validateAccess().then(response => {
        if (response.error || !response.data?.valid) {
          client.sendError('ACCESS_DENIED', response.error || 'Invalid partner/user access')
          return
        }
      })
    }
    
    // Enable auto height immediately
    client.enableAutoHeight()
    
    setEmbedClient(client)
    setIsInitialized(false) // Reset initialization flag for new client
    
    return () => {
      // Cleanup
      setEmbedClient(null)
      setIsInitialized(false)
    }
  }, [partnerId, userId, apiClient])
  
  // Send ready message only after all data is loaded
  useEffect(() => {
    if (!embedClient || loading || isInitialized) return
    
    // Initialize and send ready when everything is loaded
    embedClient.initialize({
      mode: dataMode,
      integrations_count: integrations.length,
      features: ['search', 'categories', 'bulk_actions']
    })
    
    setIsInitialized(true)
  }, [embedClient, loading, dataMode, integrations.length, isInitialized])


  // Handle connect
  const handleConnect = async (integrationType: string) => {
    try {
      setLoading(true)
      
      if (dataMode === "demo") {
        // Demo mode - simulate OAuth
        await simulateDemoOAuth(integrationType)
      } else if (dataMode === "sandbox") {
        // Sandbox mode - instant connection
        await connectSandboxIntegration(integrationType)
      } else {
        // Production mode - real OAuth
        await startRealOAuth(integrationType)
      }
      embedClient?.startOAuth(integrationType)
      
      // Demo mode continues with simulation
      
      // Update local state
      setIntegrations(prev => prev.map(integration => 
        integration.type === integrationType
          ? { ...integration, is_connected: true, connected_at: new Date().toISOString(), status: "connected" as const }
          : integration
      ))
      
      // Send success message
      const connectedIntegration = integrations.find(i => i.type === integrationType)
      if (connectedIntegration) {
        embedClient?.onIntegrationConnected(connectedIntegration as Integration)
      }
      
      toast.success(`Successfully connected ${connectedIntegration?.name}!`)
    } catch (error) {
      embedClient?.sendError('CONNECTION_FAILED', `Failed to connect ${integrationType}`)
      toast.error(`Failed to connect ${integrationType}`)
    } finally {
      setLoading(false)
    }
  }

  // Handle disconnect
  const handleDisconnect = async (integrationId: string) => {
    const integration = integrations.find(i => i.id === integrationId)
    
    if (!integration || !apiClient) {
      toast.error('Integration not found')
      return
    }
    
    try {
      setLoading(true)
      
      // Call API to disconnect
      const response = await apiClient.disconnectIntegration(integration.type)
      
      if (response.error) {
        throw new Error(response.error)
      }
      
      // Update local state
      setIntegrations(prev => prev.map(i => 
        i.id === integrationId
          ? { ...i, is_connected: false, connected_at: undefined, status: "disconnected" as const }
          : i
      ))
      
      // Send disconnect message
      embedClient?.onIntegrationDisconnected(integration as Integration)
      
      toast.success('Integration disconnected')
    } catch (error: any) {
      embedClient?.sendError('DISCONNECT_FAILED', error.message || 'Failed to disconnect integration')
      toast.error(error.message || 'Failed to disconnect')
    } finally {
      setLoading(false)
    }
  }

  // Handle settings
  const handleSettings = (integrationId: string) => {
    const integration = integrations.find(i => i.id === integrationId)
    embedClient?.sendMessage('protobox-settings-requested', { integration })
  }

  // Refresh integrations from API
  const refreshIntegrations = async () => {
    if (!apiClient || !partnerFilter) return
    
    try {
      const response = await apiClient.getAvailableIntegrations()
      if (response.data) {
        const integrationsData = partnerFilter.filterIntegrations(response.data.map(mapAPIIntegration))
        setIntegrations(integrationsData)
      }
    } catch (error) {
    }
  }
  
  // Handle refresh
  const handleRefresh = async (integrationId: string) => {
    try {
      setLoading(true)
      toast.info('Refreshing...')
      
      if (integrationId) {
        // Refresh specific integration
        if (apiClient) {
          const response = await apiClient.getIntegrationStatus(integrationId)
          if (response.data) {
            setIntegrations(prev => prev.map(integration => 
              integration.id === integrationId
                ? { ...integration, ...mapAPIIntegration(response.data!) }
                : integration
            ))
          }
        }
      } else {
        // Refresh all integrations
        await refreshIntegrations()
      }
      
      toast.success('Refreshed')
    } catch (error) {
      toast.error('Failed to refresh')
    } finally {
      setLoading(false)
    }
  }

  // Apply theme
  useEffect(() => {
    document.documentElement.classList.remove("light", "dark")
    document.documentElement.classList.add(theme)
  }, [theme])
  
  // Update data mode in client
  useEffect(() => {
    if (embedClient && dataMode) {
      embedClient.sendMessage('protobox-mode-changed', { mode: dataMode })
    }
  }, [dataMode, embedClient])


  // Helper functions for different modes
  const simulateDemoOAuth = async (integrationType: string) => {
    // Open a demo popup that auto-closes
    const popup = window.open(
      `/integrations/demo-oauth?integration=${integrationType}`,
      'oauth-popup',
      'width=600,height=700,left=100,top=100'
    )
    
    // Auto-close after 2 seconds
    setTimeout(() => {
      popup?.close()
    }, 2000)
    
    await new Promise(resolve => setTimeout(resolve, 2000))
  }
  
  const connectSandboxIntegration = async (integrationType: string) => {
    // Instant connection for sandbox
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  
  const startRealOAuth = async (integrationType: string) => {
    try {
      if (!apiClient) {
        throw new Error('API client not initialized')
      }
      
      // Call partner API to start OAuth
      const response = await apiClient.connectIntegration(integrationType)
      
      if (response.error) {
        throw new Error(response.error)
      }
      
      const data = response.data
      
      if (data.authorization_url) {
        // Open OAuth popup
        const popup = window.open(
          data.authorization_url,
          'oauth-popup',
          'width=600,height=700,left=100,top=100,scrollbars=yes,resizable=yes'
        )

        if (!popup) {
          throw new Error('Please allow popups to connect integrations')
        }

        // Poll for popup closure
        const checkClosed = setInterval(() => {
          try {
            if (popup.closed) {
              clearInterval(checkClosed)
              // Refresh integrations after a short delay
              setTimeout(async () => {
                await refreshIntegrations()
              }, 1000)
            }
          } catch (error) {
            // Cross-origin error is expected
          }
        }, 1000)

        // Listen for OAuth success/error messages
        const messageListener = async (event: MessageEvent) => {
          if (event.origin !== window.location.origin) return
          
          if (event.data.type === 'OAUTH_SUCCESS') {
            clearInterval(checkClosed)
            window.removeEventListener('message', messageListener)
            popup.close()
            
            // Refresh integrations from API to get updated status
            await refreshIntegrations()
            
            // Notify parent
            const connectedIntegration = integrations.find(i => i.type === integrationType)
            if (connectedIntegration) {
              embedClient?.onIntegrationConnected(connectedIntegration as Integration)
            }
            
            toast.success(`Successfully connected ${integrationType}!`)
          } else if (event.data.type === 'OAUTH_ERROR') {
            clearInterval(checkClosed)
            window.removeEventListener('message', messageListener)
            popup.close()
            embedClient?.sendError('OAUTH_FAILED', event.data.error || 'OAuth failed')
            toast.error('Failed to connect integration')
          }
        }

        window.addEventListener('message', messageListener)

        // Cleanup after 5 minutes
        setTimeout(() => {
          clearInterval(checkClosed)
          window.removeEventListener('message', messageListener)
          if (!popup.closed) {
            popup.close()
            embedClient?.sendError('OAUTH_TIMEOUT', 'Connection timed out')
          }
        }, 5 * 60 * 1000)
      }
    } catch (error: any) {
      embedClient?.sendError('OAUTH_ERROR', error.message || 'Failed to start OAuth')
      toast.error(error.message || 'Failed to connect')
      // Fall back to demo for now
      await simulateDemoOAuth(integrationType)
    }
  }

  // Helper function to convert hex to rgba
  const hexToRgba = (hex: string, alpha: number = 1) => {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)  
    const b = parseInt(hex.slice(5, 7), 16)
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
  }

  // Get filtered integrations
  const connectedIntegrations = integrations.filter(i => i.is_connected)
  const availableIntegrations = integrations.filter(i => !i.is_connected)

  // Determine which integrations to show based on active tab
  const displayedIntegrations = activeTab === "all" 
    ? integrations 
    : activeTab === "connected" 
      ? connectedIntegrations 
      : availableIntegrations
      
  // Get partner-specific categories
  const categories = partnerFilter ? partnerFilter.getCategories(integrations) : [
    { id: 'all', name: 'All', count: integrations.length }
  ]
  
  // Get partner branding
  const branding = partnerFilter?.getBranding() || {}

  // Background style
  const backgroundStyle = bgFrom && bgTo 
    ? { background: `linear-gradient(to bottom right, ${hexToRgba(bgFrom, 0.1)}, ${hexToRgba(bgTo, 0.1)})` }
    : {}

  return (
    <div 
      className="min-h-screen p-6"
      style={backgroundStyle}
    >
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 
            className="text-3xl font-bold text-gray-900 dark:text-white"
            style={branding.primaryColor ? { color: branding.primaryColor } : {}}
          >
            Integrations
          </h1>
          <p className="text-gray-600 dark:text-gray-300 mt-2">
            {partnerFilter?.getPartnerProfile()?.name ? 
              `Connect your tools with ${partnerFilter.getPartnerProfile()?.name}` :
              'Connect your tools to enhance your workflow'
            }
          </p>
          {partnerFilter?.getPartnerProfile() && (
            <div className="mt-2 text-sm text-muted-foreground">
              Partner: {partnerFilter.getPartnerProfile()?.name} • 
              Tier: {partnerFilter.getPartnerProfile()?.tier} • 
              {integrations.length} integrations available
            </div>
          )}
        </div>

        {/* Category Filter */}
        {categories.length > 1 && (
          <div className="mb-4">
            <div className="flex flex-wrap gap-2">
              {categories.map(category => (
                <button
                  key={category.id}
                  onClick={() => {
                    // TODO: Implement category filtering
                  }}
                  className="px-3 py-1 text-sm rounded-full border hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  {category.name}
                  {category.count > 0 && (
                    <span className="ml-1 text-xs text-gray-500">({category.count})</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
        
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList 
            className="grid w-full grid-cols-3 mb-6"
            style={branding.primaryColor ? {
              '--primary': branding.primaryColor
            } as React.CSSProperties : {}}
          >
            <TabsTrigger value="all" className="relative">
              All
              {integrations.length > 0 && (
                <Badge variant="secondary" className="ml-2 h-5 px-1.5">
                  {integrations.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="connected" className="relative">
              Connected
              {connectedIntegrations.length > 0 && (
                <Badge variant="default" className="ml-2 h-5 px-1.5 bg-green-100 text-green-800">
                  {connectedIntegrations.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="available" className="relative">
              Available
              {availableIntegrations.length > 0 && (
                <Badge variant="secondary" className="ml-2 h-5 px-1.5">
                  {availableIntegrations.length}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value={activeTab} className="mt-0">
            <ProtoBoxIntegrations
              integrations={displayedIntegrations}
              loading={loading}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              onSettings={handleSettings}
              onRefresh={handleRefresh}
              partnerBranding={branding}
              className="animate-in fade-in duration-500"
            />

            {displayedIntegrations.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-500 dark:text-gray-400">
                  {activeTab === "connected" 
                    ? "No integrations connected yet" 
                    : partnerFilter?.getPartnerProfile() 
                      ? `No integrations available for ${partnerFilter.getPartnerProfile()?.name}`
                      : "No integrations available"}
                </p>
                {partnerFilter?.getPartnerProfile()?.tier === 'free' && (
                  <p className="text-sm text-gray-400 mt-2">
                    Upgrade to Pro or Enterprise for more integrations
                  </p>
                )}
              </div>
            )}
          </TabsContent>
        </Tabs>

        <div className="mt-8 text-center">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Powered by{" "}
            <a 
              href="https://github.com/chanl-ai/protobox-python" 
              target="_blank" 
              rel="noopener noreferrer"
              className="font-medium text-blue-600 dark:text-blue-400 hover:underline"
            >
              ProtoBox
            </a>
            {dataMode === "demo" && (
              <Badge variant="outline" className="ml-2 text-xs">
                Demo Mode
              </Badge>
            )}
          </p>
        </div>
      </div>

      <Toaster 
        position="bottom-right"
        toastOptions={{
          style: {
            background: theme === "dark" ? '#1e293b' : '#fff',
            color: theme === "dark" ? '#f1f5f9' : '#0f172a',
            border: `1px solid ${theme === "dark" ? '#334155' : '#e2e8f0'}`
          }
        }}
      />
    </div>
  )
}

export default function IntegrationsPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading ProtoBox...</p>
        </div>
      </div>
    }>
      <IntegrationsContent />
    </Suspense>
  )
}