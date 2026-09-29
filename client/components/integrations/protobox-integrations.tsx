"use client"

import * as React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { 
  Plug,
  Settings,
  RefreshCw,
  Check,
  AlertTriangle,
  Loader2,
  X
} from "lucide-react"
import { cn } from "@/lib/utils"

// Import brand icons from simple-icons
import {
  siGoogle,
  siHubspot,
  siGmail,
  siSlack,
  siShopify,
  siStripe,
  siSalesforce
} from 'simple-icons'

// Brand icon component matching admin UI
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

// Helper function to get simple icon based on integration type (matches admin UI)
function getSimpleIcon(integrationType: string) {
  const iconMap: Record<string, any> = {
    'google_calendar': siGoogle,
    'hubspot': siHubspot,
    'gmail': siGmail,
    'slack': siSlack,
    'shopify': siShopify,
    'stripe': siStripe,
    'salesforce': siSalesforce
  }
  return iconMap[integrationType] || siGoogle // fallback to Google icon
}

interface Integration {
  id: string
  type: string
  name: string
  description: string
  icon?: string
  is_connected: boolean
  connected_at?: string
  config?: Record<string, any>
  status?: 'connected' | 'error' | 'disconnected'
  permissions?: {
    connect: boolean
    disconnect: boolean
    configure: boolean
  }
  priority?: number
  category?: string
}

interface ProtoBoxIntegrationsProps {
  integrations: Integration[]
  loading?: boolean
  onConnect: (integrationType: string) => Promise<void>
  onDisconnect?: (integrationId: string) => Promise<void>
  onSettings?: (integrationId: string) => void
  onRefresh?: (integrationId: string) => Promise<void>
  className?: string
  partnerBranding?: {
    primaryColor?: string
    logo?: string
  }
}

export function ProtoBoxIntegrations({
  integrations,
  loading = false,
  onConnect,
  onDisconnect,
  onSettings,
  onRefresh,
  className,
  partnerBranding
}: ProtoBoxIntegrationsProps) {
  const [connectingId, setConnectingId] = React.useState<string | null>(null)
  const [refreshingId, setRefreshingId] = React.useState<string | null>(null)

  const handleConnect = async (integration: Integration) => {
    if (integration.is_connected || !integration.permissions?.connect) return
    
    setConnectingId(integration.type)
    try {
      await onConnect(integration.type)
    } finally {
      setConnectingId(null)
    }
  }

  const handleRefresh = async (integration: Integration) => {
    if (!onRefresh) return
    
    setRefreshingId(integration.id)
    try {
      await onRefresh(integration.id)
    } finally {
      setRefreshingId(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">Loading integrations...</p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("space-y-6", className)}>
      <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
        {integrations.map((integration) => {
          const isConnecting = connectingId === integration.type
          const isRefreshing = refreshingId === integration.id
          
          return (
            <Card key={integration.id} className="flex min-h-[140px] flex-col transition hover:shadow-md">
              <CardHeader className="flex-1 pb-4">
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
                    <BrandIcon 
                      icon={getSimpleIcon(integration.type)} 
                      className="h-6 w-6 text-muted-foreground"
                    />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base font-medium">
                        {integration.name}
                      </CardTitle>
                      {integration.is_connected && (
                        <Badge variant="default" className="ml-2 bg-green-100 text-green-800 hover:bg-green-100">
                          <Check className="w-3 h-3 mr-1" />
                          Connected
                        </Badge>
                      )}
                      {integration.status === 'error' && (
                        <Badge variant="destructive" className="ml-2">
                          <AlertTriangle className="w-3 h-3 mr-1" />
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
                  {!integration.is_connected && (
                    <Button 
                      size="sm" 
                      className="flex-1" 
                      onClick={() => handleConnect(integration)}
                      disabled={isConnecting || !integration.permissions?.connect}
                      style={partnerBranding?.primaryColor && !isConnecting ? {
                        backgroundColor: integration.permissions?.connect ? partnerBranding.primaryColor : undefined
                      } : {}}
                    >
                      {isConnecting ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Plug className="w-4 h-4 mr-2" />
                      )}
                      {isConnecting ? "Connecting..." : 
                       integration.permissions?.connect ? "Connect" : "Not Available"}
                    </Button>
                  )}
                  
                  {integration.is_connected && (
                    <>
                      {onSettings && integration.permissions?.configure && (
                        <Button 
                          size="sm" 
                          variant="outline" 
                          className="flex-1"
                          onClick={() => onSettings(integration.id)}
                        >
                          <Settings className="w-4 h-4 mr-2" />
                          Settings
                        </Button>
                      )}
                      {onRefresh && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => handleRefresh(integration)}
                          disabled={isRefreshing}
                          title="Refresh integration"
                        >
                          <RefreshCw className={cn(
                            "w-4 h-4",
                            isRefreshing && "animate-spin"
                          )} />
                        </Button>
                      )}
                      {onDisconnect && integration.permissions?.disconnect && (
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => onDisconnect(integration.id)}
                          title="Disconnect integration"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      )}
                      {!integration.permissions?.disconnect && (
                        <div className="text-xs text-muted-foreground px-2 py-1">
                          Managed by partner
                        </div>
                      )}
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