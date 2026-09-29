"use client"

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import { 
  IconPlug,
  IconSettings,
  IconRefresh,
  IconCheck,
  IconAlertTriangle
} from '@tabler/icons-react'
import { embedApiClient } from '@/lib/api/embed-client'
import { AuthProvider } from '@/lib/auth/auth-context'

// Available integrations configuration
const availableIntegrations = [
  {
    id: 'google_calendar',
    name: 'Google Calendar',
    description: 'Schedule appointments and manage calendar events',
    category: 'productivity',
    status: 'available' as const,
    brandIcon: null, // We'll add icons later
  },
  {
    id: 'hubspot',
    name: 'HubSpot CRM',
    description: 'Manage contacts, deals, and customer relationships',
    category: 'crm',
    status: 'available' as const,
    brandIcon: null,
  }
]

interface IntegrationsCoreProps {
  authProvider: AuthProvider
  authToken: string
  workspaceId: string
  isEmbedded?: boolean
  onOAuthStart?: (integrationType: string, authUrl: string) => void
  onNavigate?: (path: string) => void
}

interface ConnectedIntegration {
  _id: string
  integration_type: string
  status: string
  connected_at?: string
  error_message?: string
}

export function IntegrationsCore({
  authProvider,
  authToken,
  workspaceId,
  isEmbedded = false,
  onOAuthStart,
  onNavigate
}: IntegrationsCoreProps) {
  const [connectedIntegrations, setConnectedIntegrations] = useState<ConnectedIntegration[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [connectingIntegration, setConnectingIntegration] = useState<string | null>(null)
  const [resettingIntegration, setResettingIntegration] = useState<string | null>(null)

  // Configure API client
  useEffect(() => {
    embedApiClient.configure({
      provider: authProvider,
      token: authToken,
      workspaceId,
      partnerSignature: authProvider === 'partner' ? authToken : undefined
    })
  }, [authProvider, authToken, workspaceId])

  // Load integrations
  useEffect(() => {
    async function loadIntegrations() {
      try {
        setIsLoading(true)
        const data = await embedApiClient.get('/integrations')
        setConnectedIntegrations(data)
      } catch (error) {
        toast.error('Failed to load integrations')
      } finally {
        setIsLoading(false)
      }
    }

    if (authToken) {
      loadIntegrations()
    }
  }, [authToken])

  const handleConnect = async (integrationType: string) => {
    setConnectingIntegration(integrationType)
    
    try {
      const response = await embedApiClient.post(`/integrations/${integrationType}/connect`, {})
      
      if (response.authorization_url) {
        if (isEmbedded && onOAuthStart) {
          // In embed mode, let parent handle OAuth
          onOAuthStart(integrationType, response.authorization_url)
        } else {
          // In standalone mode, open popup
          const popup = window.open(
            response.authorization_url,
            'oauth-popup',
            'width=500,height=600,scrollbars=yes,resizable=yes'
          )

          if (!popup) {
            toast.error('Please allow popups to connect integrations')
            return
          }

          // Listen for OAuth completion
          const checkClosed = setInterval(() => {
            if (popup.closed) {
              clearInterval(checkClosed)
              // Reload integrations after a delay
              setTimeout(() => {
                window.location.reload()
              }, 1000)
            }
          }, 1000)
        }
      }
    } catch (error) {
      toast.error('Failed to connect integration')
    } finally {
      setConnectingIntegration(null)
    }
  }

  const handleReset = async (integrationType: string) => {
    setResettingIntegration(integrationType)
    
    try {
      const result = await embedApiClient.post(`/integrations/${integrationType}/reset`, {})
      toast.success(`Reset complete: ${result.deleted_actions} actions deleted, ${result.created_actions} actions created`)
      
      // Reload integrations
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    } catch (error) {
      toast.error('Failed to reset integration')
    } finally {
      setResettingIntegration(null)
    }
  }

  const handleSettings = (integrationType: string) => {
    if (isEmbedded && onNavigate) {
      // In embed mode, notify parent
      onNavigate(`/integrations/${integrationType}/settings`)
    } else {
      // In standalone mode, navigate
      window.location.href = `/dashboard/integrations/${integrationType}/settings`
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading integrations...</p>
        </div>
      </div>
    )
  }

  const getIntegrationStatus = (integrationType: string) => {
    const connected = connectedIntegrations.find(c => c.integration_type === integrationType)
    return connected?.status || 'disconnected'
  }

  return (
    <div className={isEmbedded ? 'p-4' : 'space-y-6'}>
      {!isEmbedded && (
        <>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Integrations</h1>
            <p className="text-gray-600 mt-2">
              Connect your favorite tools to enable powerful AI-driven automations.
            </p>
          </div>
          <Separator />
        </>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {availableIntegrations.map((integration) => {
          const status = getIntegrationStatus(integration.id)
          const isConnected = status === 'connected'
          const isConnecting = connectingIntegration === integration.id
          const isResetting = resettingIntegration === integration.id

          return (
            <Card key={integration.id} className="flex min-h-[140px] flex-col transition hover:shadow-md">
              <CardHeader className="flex-1 pb-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
                    <IconPlug className="h-6 w-6" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base font-medium">
                        {integration.name}
                      </CardTitle>
                      {isConnected && (
                        <Badge variant="success" className="ml-2">
                          <IconCheck className="w-3 h-3 mr-1" />
                          Connected
                        </Badge>
                      )}
                      {status === 'error' && (
                        <Badge variant="destructive" className="ml-2">
                          <IconAlertTriangle className="w-3 h-3 mr-1" />
                          Error
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
                
                <CardDescription className="text-xs leading-snug text-muted-foreground">
                  {integration.description}
                </CardDescription>
              </CardHeader>
              
              <CardContent className="pt-0">
                <div className="flex gap-2">
                  {!isConnected && (
                    <Button 
                      size="sm" 
                      className="flex-1" 
                      onClick={() => handleConnect(integration.id)}
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
                        onClick={() => handleSettings(integration.id)}
                      >
                        <IconSettings className="w-4 h-4 mr-2" />
                        Settings
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => handleReset(integration.id)}
                        disabled={isResetting}
                      >
                        <IconRefresh className={`w-4 h-4 ${isResetting ? 'animate-spin' : ''}`} />
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}