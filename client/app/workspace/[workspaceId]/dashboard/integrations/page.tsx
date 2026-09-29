"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/lib/auth"
import { useWorkspaceReady } from "@/hooks"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { protoboxClient } from "@/lib/api/protobox-client"
import { 
  IconCalendar, 
  IconUsers,
  IconMail,
  IconMessages,
  IconShoppingCart,
  IconCreditCard,
  IconFileText,
  IconSettings,
  IconPlug,
  IconCheck,
  IconAlertTriangle,
  IconX,
  IconRefresh
} from "@tabler/icons-react"

// Import brand icons from simple-icons
import {
  siGoogle,
  siHubspot,
  siGmail,
  siSlack,
  siShopify,
  siStripe
} from 'simple-icons'

// Brand icon component
function BrandIcon({ icon, className }: { icon: any, className?: string }) {
  return (
    <svg
      role="img" 
      viewBox="0 0 24 24"
      className={className}
      fill="currentColor"
    >
      <path d={icon.path} />
    </svg>
  )
}

// Mock data for available integrations
const availableIntegrations = [
  {
    id: "google_calendar",
    name: "Google Calendar",
    description: "Schedule appointments and manage calendar events through voice and chat",
    category: "productivity",
    brandIcon: siGoogle,
    status: "available",
    features: ["Schedule appointments", "Check availability", "Voice-optimized responses"]
  },
  {
    id: "hubspot",
    name: "HubSpot CRM",
    description: "Manage contacts, deals, and customer relationships",
    category: "crm",
    brandIcon: siHubspot,
    status: "available",
    features: ["Create contacts", "Log activities", "Update deals", "Voice interaction"]
  },
  {
    id: "gmail",
    name: "Gmail",
    description: "Send and manage emails through AI assistants",
    category: "communication",
    brandIcon: siGmail,
    status: "coming_soon",
    features: ["Send emails", "Read inbox", "Schedule emails"]
  },
  {
    id: "slack",
    name: "Slack",
    description: "Send messages and manage team communication",
    category: "communication",
    brandIcon: siSlack,
    status: "coming_soon",
    features: ["Send messages", "Channel management", "Team notifications"]
  },
  {
    id: "shopify",
    name: "Shopify",
    description: "Manage your online store and orders",
    category: "ecommerce",
    brandIcon: siShopify,
    status: "coming_soon",
    features: ["Order management", "Inventory tracking", "Customer support"]
  },
  {
    id: "stripe",
    name: "Stripe",
    description: "Process payments and manage subscriptions",
    category: "finance",
    brandIcon: siStripe,
    status: "coming_soon",
    features: ["Payment processing", "Subscription management", "Invoice creation"]
  }
]

// API functions for fetching real data
async function fetchAvailableIntegrations() {
  try {
    const response = await protoboxClient.getAvailableIntegrations()
    if (response.error) {
      throw new Error(response.error)
    }
    const backendData = response.data || []
    
    // Map backend data structure to frontend structure
    return (Array.isArray(backendData) ? backendData : []).map((integration: any) => ({
      id: integration.integration_type,
      name: integration.display_name,
      description: integration.description,
      category: integration.category,
      brandIcon: getSimpleIcon(integration.integration_type),
      status: "available", // all backend integrations are available
      features: integration.available_actions?.map((action: any) => action.description) || []
    }))
  } catch (error) {
    return availableIntegrations // fallback to mock data
  }
}

// Helper function to get simple icon based on integration type
function getSimpleIcon(integrationType: string) {
  const iconMap: Record<string, any> = {
    'google_calendar': siGoogle,
    'hubspot': siHubspot,
    'gmail': siGmail,
    'slack': siSlack,
    'shopify': siShopify,
    'stripe': siStripe
  }
  return iconMap[integrationType] || siGoogle // fallback to Google icon
}

async function fetchWorkspaceIntegrations(workspaceId: string | undefined) {
  if (!workspaceId) return []
  try {
    const response = await protoboxClient.getWorkspaceIntegrations(workspaceId)
    if (response.error) {
      throw new Error(response.error)
    }
    return response.data || []
  } catch (error) {
    return [] // no connected integrations
  }
}


function getStatusBadge(integrationId: string, connectedIntegrations: ConnectedIntegration[], status?: string) {
  const connected = connectedIntegrations.find(c => c.integration_type === integrationId)
  
  if (connected) {
    switch (connected.status) {
      case "connected":
        return <IconCheck className="w-4 h-4 text-green-600" />
      case "error":
        return <IconAlertTriangle className="w-4 h-4 text-red-600" />
      case "setup":
        return <IconSettings className="w-4 h-4 text-orange-600" />
      default:
        return null
    }
  }
  
  return null
}

// API functions
async function resetIntegrationActions(workspaceId: string | undefined, integrationType: string) {
  if (!workspaceId) throw new Error('Workspace ID required')
  try {
    const response = await protoboxClient.resetIntegrationActions(workspaceId, integrationType)

    if (response.error) {
      throw new Error(response.error)
    }

    const data = response.data as any
    return data
    
  } catch (error) {
    toast.error('Failed to reset integration actions')
    throw error
  }
}

async function startIntegrationConnection(workspaceId: string, integrationType: string) {
  try {
    const response = await apiClient.post(`/workspaces/${workspaceId}/integrations/${integrationType}/connect`)

    if (response.error) {
      throw new Error(response.error)
    }

    const data = response.data
    
    // For OAuth2 integrations, open popup window
    if (data.authorization_url) {
      return new Promise((resolve, reject) => {
        // Open popup window for OAuth
        const popup = window.open(
          data.authorization_url,
          'oauth-popup',
          'width=500,height=600,scrollbars=yes,resizable=yes'
        )

        if (!popup) {
          toast.error('Please allow popups for this site to connect integrations')
          reject(new Error('Popup blocked'))
          return
        }

        // Poll for popup closure or success
        const checkClosed = setInterval(() => {
          try {
            if (popup.closed) {
              clearInterval(checkClosed)
              // Check if integration was successful by refetching data
              setTimeout(() => {
                window.location.reload() // Simple refresh to update integration status
              }, 1000)
              resolve(undefined)
            }
          } catch (error) {
            // Cross-origin access error is expected
          }
        }, 1000)

        // Listen for success message from popup
        const messageListener = (event: MessageEvent) => {
          if (event.origin !== window.location.origin) return
          
          if (event.data.type === 'OAUTH_SUCCESS') {
            clearInterval(checkClosed)
            window.removeEventListener('message', messageListener)
            popup.close()
            toast.success(`${integrationType} connected successfully!`)
            setTimeout(() => {
              window.location.reload() // Refresh to show connected status
            }, 1000)
            resolve(undefined)
          } else if (event.data.type === 'OAUTH_ERROR') {
            clearInterval(checkClosed)
            window.removeEventListener('message', messageListener)
            popup.close()
            toast.error('Failed to connect integration')
            reject(new Error(event.data.error))
          }
        }

        window.addEventListener('message', messageListener)

        // Cleanup after 5 minutes
        setTimeout(() => {
          clearInterval(checkClosed)
          window.removeEventListener('message', messageListener)
          if (!popup.closed) {
            popup.close()
            toast.error('Integration connection timed out')
            reject(new Error('Timeout'))
          }
        }, 5 * 60 * 1000)
      })
    }
    
    // For other integrations, handle setup instructions
    if (data?.setup_required) {
      toast.info(data.instructions as string)
      return
    }
    
  } catch (error) {
    toast.error('Failed to connect integration')
  }
}

interface ConnectedIntegration {
  integration_type: string
  status: string
  actionsCount?: number
}

function IntegrationCard({ integration, connectedIntegrations }: { 
  integration: typeof availableIntegrations[0], 
  connectedIntegrations: ConnectedIntegration[] 
}) {
  const { workspaceId } = useWorkspaceReady()
  const [isConnecting, setIsConnecting] = useState(false)
  const [isResetting, setIsResetting] = useState(false)
  
  const connected = connectedIntegrations.find(c => c.integration_type === integration.id)
  const isConnected = connected?.status === "connected"
  const isAvailable = integration.status === "available"
  
  const handleConnect = async () => {
    setIsConnecting(true)
    try {
      await startIntegrationConnection(workspaceId || undefined, integration.id)
    } finally {
      setIsConnecting(false)
    }
  }
  
  const handleReset = async () => {
    setIsResetting(true)
    try {
      const result = await resetIntegrationActions(workspaceId || undefined, integration.id) as any
      toast.success(`Reset complete: ${result?.deleted_actions || 0} actions deleted, ${result?.created_actions || 0} actions created`)
      // Refresh the page to show updated status
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    } catch (error) {
      // Error already handled in resetIntegrationActions
    } finally {
      setIsResetting(false)
    }
  }
  
  return (
    <Card className="flex min-h-[140px] flex-col transition hover:shadow-md">
      <CardHeader className="flex-1 pb-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
            <BrandIcon icon={integration.brandIcon} className="h-6 w-6" />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-medium">{integration.name}</CardTitle>
              {getStatusBadge(integration.id, connectedIntegrations, integration.status)}
            </div>
          </div>
        </div>
        
        <CardDescription className="text-xs leading-snug text-muted-foreground">
          {integration.description}
        </CardDescription>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="flex gap-2">
          {!isConnected && isAvailable && (
            <Button 
              size="sm" 
              className="flex-1" 
              onClick={handleConnect}
              disabled={isConnecting}
            >
              <IconPlug className="w-4 h-4 mr-2" />
              {isConnecting ? "Connecting..." : "Connect"}
            </Button>
          )}
          
          {isConnected && (
            <>
              <Button size="sm" variant="outline" className="flex-1">
                <IconSettings className="w-4 h-4 mr-2" />
                Settings
              </Button>
              <Button 
                size="sm" 
                variant="outline"
                onClick={handleReset}
                disabled={isResetting}
                title="Reset integration actions"
              >
                <IconRefresh className={`w-4 h-4 ${isResetting ? 'animate-spin' : ''}`} />
              </Button>
              <Button size="sm" variant="outline">
                <IconX className="w-4 h-4" />
              </Button>
            </>
          )}
          
          {!isAvailable && (
            <Button size="sm" variant="outline" disabled className="flex-1">
              Coming Soon
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function IntegrationsPage() {
  const { workspaceId, isReady } = useWorkspaceReady()
  const [selectedCategory, setSelectedCategory] = useState("all")
  const [availableIntegrationsData, setAvailableIntegrationsData] = useState(availableIntegrations)
  const [connectedIntegrations, setConnectedIntegrations] = useState<ConnectedIntegration[]>([])
  const [isLoading, setIsLoading] = useState(true)
  
  // Fetch real data on component mount
  useEffect(() => {
    async function loadData() {
      if (!isReady || !workspaceId) return
      
      setIsLoading(true)
      try {
        const [available, connected] = await Promise.all([
          fetchAvailableIntegrations(),
          fetchWorkspaceIntegrations(workspaceId)
        ])
        setAvailableIntegrationsData(available)
        setConnectedIntegrations(connected as ConnectedIntegration[])
      } catch (error) {
        toast.error('Failed to load integrations')
      } finally {
        setIsLoading(false)
      }
    }
    
    loadData()
  }, [workspaceId, isReady])
  
  const filteredIntegrations = availableIntegrationsData.filter(integration => 
    selectedCategory === "all" || integration.category === selectedCategory
  )
  
  const connectedCount = connectedIntegrations.filter(c => c.status === "connected").length
  
  // Generate categories dynamically based on current data
  const categories = [
    { id: "all", name: "All", count: availableIntegrationsData.length },
    { id: "productivity", name: "Productivity", count: availableIntegrationsData.filter(i => i.category === "productivity").length },
    { id: "crm", name: "CRM", count: availableIntegrationsData.filter(i => i.category === "crm").length },
    { id: "communication", name: "Communication", count: availableIntegrationsData.filter(i => i.category === "communication").length },
    { id: "ecommerce", name: "E-commerce", count: availableIntegrationsData.filter(i => i.category === "ecommerce").length },
    { id: "finance", name: "Finance", count: availableIntegrationsData.filter(i => i.category === "finance").length }
  ]
  
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
          <p className="text-gray-600 mt-2">Loading integrations...</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
        <p className="text-gray-600 mt-2">
          Connect your favorite tools to enable powerful AI-driven automations. 
          {connectedCount > 0 && ` You have ${connectedCount} integration${connectedCount !== 1 ? 's' : ''} connected.`}
        </p>
      </div>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Connected</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-2xl font-bold text-green-600">{connectedCount}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Available</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-2xl font-bold text-blue-600">
              {availableIntegrationsData.filter(i => i.status === "available").length}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Actions</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-2xl font-bold text-purple-600">
              {connectedIntegrations.reduce((sum, c) => sum + (c.actionsCount || 0), 0)}
            </div>
          </CardContent>
        </Card>
      </div>
      
      <Separator />
      
      {/* Category Filter */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Categories</h2>
        <div className="flex flex-wrap gap-2">
          {categories.map(category => (
            <Button
              key={category.id}
              variant={selectedCategory === category.id ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(category.id)}
              className="h-8"
            >
              {category.name}
              {category.count > 0 && (
                <Badge variant="secondary" className="ml-2 h-5 px-1.5 text-xs">
                  {category.count}
                </Badge>
              )}
            </Button>
          ))}
        </div>
      </div>
      
      {/* Integrations Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {filteredIntegrations.map(integration => (
          <IntegrationCard 
            key={integration.id} 
            integration={integration} 
            connectedIntegrations={connectedIntegrations} 
          />
        ))}
      </div>
      
      {filteredIntegrations.length === 0 && (
        <div className="text-center py-12">
          <IconPlug className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No integrations found</h3>
          <p className="text-gray-600">Try selecting a different category or check back later for new integrations.</p>
        </div>
      )}
    </div>
  )
}