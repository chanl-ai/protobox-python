"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { useWorkspaceReady } from "@/hooks"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { protoboxClient } from "@/lib/api/protobox-client"
import { IntegrationSettingsDialog } from "@/components/integrations/integration-settings-dialog"
import { IntegrationConnectDialog } from "@/components/integrations/integration-connect-dialog"
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

// Import integration icons from our centralized icon system
import { getIntegrationIcon, hasIntegrationIcon } from '@/lib/icons/integration-icons'

// Brand icon component
function BrandIcon({ icon, className }: { icon: any, className?: string }) {
  if (!icon) {
    return (
      <div className={`w-6 h-6 rounded bg-muted flex items-center justify-center ${className}`}>
        <IconPlug className="w-4 h-4 text-muted-foreground" />
      </div>
    )
  }

  if (icon.type === 'svg') {
    return (
      <svg
        role="img" 
        viewBox="0 0 24 24"
        className={className}
        fill={icon.color || "currentColor"}
      >
        <path d={icon.content as string} />
      </svg>
    )
  }

  if (icon.type === 'image') {
    return (
      <img
        src={icon.content as string}
        alt="Integration icon"
        className={className}
      />
    )
  }

  // Fallback for other icon types
  return (
    <div className={`w-6 h-6 rounded bg-muted flex items-center justify-center ${className}`}>
      <IconPlug className="w-4 h-4 text-muted-foreground" />
    </div>
  )
}

// API key integrations that use the connect dialog form
const API_KEY_INTEGRATIONS = ['openai', 'stripe', 'twilio', 'sendgrid', 'notion', 'resend', 'anthropic', 'airtable']

// API functions for fetching real data
async function fetchAvailableIntegrations(): Promise<AvailableIntegration[]> {
  try {
    const { protoboxClient } = await import('@/lib/api/protobox-client')
    const response = await protoboxClient.getAvailableIntegrations()
    if (response.error) {
      throw new Error(response.error)
    }
    const backendData = response.data || []
    
    // Ensure backendData is an array before mapping
    if (!Array.isArray(backendData)) {
      return []
    }
    
    // Map backend data structure to frontend structure
    const mappedData = backendData.map((integration: any) => ({
      id: integration.integration_type,
      name: integration.display_name,
      description: integration.description,
      category: integration.category || 'other',
      brandIcon: getSimpleIcon(integration.integration_type),
      status: getIntegrationStatus(integration.integration_type),
      features: integration.available_actions?.map((action: any) => action.description) || []
    }))
    
    return mappedData
  } catch (error) {
    return []
  }
}

// Helper function to determine integration status
function getIntegrationStatus(integrationType: string) {
  // Mark certain integrations as coming soon
  const comingSoonIntegrations = ['shopify', 'salesforce', 'linkedin']
  if (comingSoonIntegrations.includes(integrationType)) {
    return 'coming_soon'
  }
  return 'available'
}

// Helper function to get icon based on integration type
function getSimpleIcon(integrationType: string) {
  // First try to get from our centralized icon system
  const icon = getIntegrationIcon(integrationType)
  if (icon) {
    return icon
  }
  
  // Fallback mapping for integrations not yet in our system
  const fallbackMap: Record<string, string> = {
    'microsoft_365': 'google_calendar', // Use Google Calendar as fallback
    'linkedin': 'github', // Use GitHub as fallback
    'gmail': 'google_gmail', // Map old gmail to new google_gmail
    'gdrive': 'google_drive', // Map old gdrive to new google_drive
    'gsheets': 'google_sheets', // Map old gsheets to new google_sheets
    'gdocs': 'google_docs', // Map old gdocs to new google_docs
    'ganalytics': 'google_analytics', // Map old ganalytics to new google_analytics
    'gads': 'google_ads', // Map old gads to new google_ads
  }
  
  const fallbackId = fallbackMap[integrationType]
  if (fallbackId) {
    return getIntegrationIcon(fallbackId) || getIntegrationIcon('google_calendar')
  }
  
  // Default fallback
  return getIntegrationIcon('google_calendar')
}

async function fetchWorkspaceIntegrations(workspaceId: string) {
  try {
    const { protoboxClient } = await import('@/lib/api/protobox-client')
    const response = await protoboxClient.getWorkspaceIntegrations(workspaceId)
    if (response.error) {
      // If endpoint doesn't exist, return empty array
      if (response.status === 404) {
        return []
      }
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
async function resetIntegrationActions(workspaceId: string, integrationType: string) {
  try {
    const { protoboxClient } = await import('@/lib/api/protobox-client')
    const response = await protoboxClient.resetIntegrationActions(workspaceId, integrationType)

    if (response.error) {
      throw new Error(response.error)
    }

    const data = response.data as { deleted_actions: number; created_actions: number }
    return data
    
  } catch (error) {
    toast.error('Failed to reset integration actions')
    throw error
  }
}

async function startIntegrationConnection(workspaceId: string, integrationType: string) {
  try {
    const { protoboxClient } = await import('@/lib/api/protobox-client')
    const response = await protoboxClient.connectIntegration(workspaceId, integrationType)


    if (response.error) {
      throw new Error(response.error)
    }

    const data = response.data as any
    
    // For OAuth2 integrations, open popup window
    if (data?.authorization_url) {
      return new Promise((resolve, reject) => {
        // Open popup window for OAuth
        const popup = window.open(
          data?.authorization_url,
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
      toast.info(data?.instructions)
      return
    }
    
  } catch (error) {
    // Don't show toast here since handleConnect will show it
    throw error
  }
}

interface ConnectedIntegration {
  integration_type: string
  status: string
  actionsCount?: number
}

// Define proper types for the integration data
interface AvailableIntegration {
  id: string
  name: string
  description: string
  category: string
  brandIcon: any
  status: string
  features: string[]
}

function IntegrationCard({ integration, connectedIntegrations, workspaceId }: { 
  integration: AvailableIntegration, 
  connectedIntegrations: ConnectedIntegration[],
  workspaceId: string
}) {
  const [isConnecting, setIsConnecting] = useState(false)
  const [isResetting, setIsResetting] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showConnectDialog, setShowConnectDialog] = useState(false)
  
  const connected = connectedIntegrations.find(c => c.integration_type === integration.id)
  const isConnected = connected?.status === "connected"
  const isAvailable = integration.status === "available"
  
  const handleConnect = async () => {
    // For API key integrations like OpenAI, show the connect dialog
    if (API_KEY_INTEGRATIONS.includes(integration.id)) {
      setShowConnectDialog(true)
      return
    }
    
    // For OAuth2 integrations (Google Calendar, etc), use the ORIGINAL OAuth popup flow
    setIsConnecting(true)
    try {
      await startIntegrationConnection(workspaceId, integration.id)
    } catch (error: any) {
      // Check if it's a 404 error
      if (error.message?.includes('404') || error.message?.includes('Not Found')) {
        toast.error('Integration connection is not yet implemented.')
      } else {
        toast.error(error.message || 'Failed to connect integration. Please try again.')
      }
    } finally {
      setIsConnecting(false)
    }
  }
  
  const handleReset = async () => {
    setIsResetting(true)
    try {
      const result = await resetIntegrationActions(workspaceId, integration.id)
      toast.success(`Reset complete: ${result.deleted_actions} actions deleted, ${result.created_actions} actions created`)
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
              <Button 
                size="sm" 
                variant="outline" 
                className="flex-1"
                onClick={() => {
                  // For API key integrations, use the new dialog
                  if (API_KEY_INTEGRATIONS.includes(integration.id)) {
                    setShowConnectDialog(true)
                  } else {
                    // For OAuth integrations, use the original settings dialog
                    setShowSettings(true)
                  }
                }}
              >
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
            </>
          )}
          
          {!isAvailable && (
            <Button size="sm" variant="outline" disabled className="flex-1">
              Coming Soon
            </Button>
          )}
        </div>
      </CardContent>
      
      {/* Original Settings Dialog - for OAuth integrations (Google Calendar, Gmail, etc) */}
      <IntegrationSettingsDialog
        integration={{
          ...integration,
          status: isConnected ? "connected" : "disconnected"
        } as any}
        open={showSettings}
        onOpenChange={setShowSettings}
        onSave={async (settings) => {
          if (!workspaceId) {
            toast.error('Workspace not ready')
            return
          }
          
          try {
            // Save settings to backend
            const response = await protoboxClient.updateIntegrationSettings(workspaceId, integration.id, settings)
            
            if (response.error) {
              toast.error(response.error)
            } else {
              toast.success('Settings saved successfully')
              setShowSettings(false)
            }
          } catch (error) {
            toast.error('Failed to save settings')
          }
        }}
        onDisconnect={async () => {
          if (!workspaceId) {
            toast.error('Workspace not ready')
            return
          }
          
          try {
            const response = await protoboxClient.disconnectIntegration(workspaceId, integration.id)
            
            if (response.error) {
              toast.error(response.error)
            } else {
              toast.success('Integration disconnected successfully')
              setShowSettings(false)
              // Reload to refresh the integration status
              window.location.reload()
            }
          } catch (error) {
            toast.error('Failed to disconnect integration')
          }
        }}
        onTestConnection={async () => {
          if (!workspaceId) {
            toast.error('Workspace not ready')
            return false
          }
          
          try {
            const response = await protoboxClient.request(`/workspaces/${workspaceId}/integrations/${integration.id}/test`, {
              method: 'POST',
            })
            
            if (response.error) {
              toast.error(response.error)
              return false
            } else {
              const data = response.data as { success: boolean; message: string }
              if (data.success) {
                toast.success(data.message || 'Connection test successful!')
              } else {
                toast.error(data.message || 'Connection test failed')
              }
              return data.success
            }
          } catch (error) {
            toast.error('Failed to test connection')
            return false
          }
        }}
      />
      
      {/* New Connect Dialog - ONLY for API key integrations (OpenAI, Stripe, Twilio, SendGrid, Notion, Resend, Anthropic, Airtable) */}
      {API_KEY_INTEGRATIONS.includes(integration.id) && (
        <IntegrationConnectDialog
          integration={{
            integration_type: integration.id,
            display_name: integration.name,
            description: integration.description,
            icon_url: null,
            is_connected: isConnected,
            status: isConnected ? "connected" : "not_connected",
            connected_at: connected ? new Date().toISOString() : null
          }}
          isOpen={showConnectDialog}
          onClose={() => setShowConnectDialog(false)}
          onConnect={() => {
            // Refresh the page to show updated status
            window.location.reload()
          }}
          workspaceId={workspaceId}
        />
      )}
    </Card>
  )
}

export default function IntegrationsPage() {
  const params = useParams()
  const { isReady, workspaceId, user, getDependencies } = useWorkspaceReady()
  const [selectedCategory, setSelectedCategory] = useState("all")
  const [availableIntegrationsData, setAvailableIntegrationsData] = useState<AvailableIntegration[]>([])
  const [connectedIntegrations, setConnectedIntegrations] = useState<ConnectedIntegration[]>([])
  const [isLoading, setIsLoading] = useState(true)
  
  // Fetch real data on component mount
  useEffect(() => {
    async function loadData() {
      if (!isReady) return
      
      setIsLoading(true)
      try {
        
        const [available, connected] = await Promise.all([
          fetchAvailableIntegrations(),
          fetchWorkspaceIntegrations(workspaceId!)
        ])
        setAvailableIntegrationsData(available)
        setConnectedIntegrations(connected as ConnectedIntegration[])
      } catch (error) {
        // Don't show error toast since we have fallback data
        // toast.error('Failed to load integrations')
      } finally {
        setIsLoading(false)
      }
    }
    
    loadData()
  }, getDependencies())
  
  const filteredIntegrations = availableIntegrationsData.filter(integration => 
    selectedCategory === "all" || integration.category === selectedCategory
  )
  
  const connectedCount = connectedIntegrations.filter(c => c.status === "connected").length
  
  // Generate categories dynamically based on current data
  const categories = [
    { id: "all", name: "All", count: availableIntegrationsData.length },
    { id: "productivity", name: "Productivity", count: availableIntegrationsData.filter(i => i.category === "productivity").length },
    { id: "communication", name: "Communication", count: availableIntegrationsData.filter(i => i.category === "communication").length },
    { id: "ai", name: "AI", count: availableIntegrationsData.filter(i => i.category === "ai").length },
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
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 auto-rows-fr">
        {filteredIntegrations.map(integration => (
          <IntegrationCard 
            key={integration.id} 
            integration={integration} 
            connectedIntegrations={connectedIntegrations}
            workspaceId={workspaceId || ""}
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