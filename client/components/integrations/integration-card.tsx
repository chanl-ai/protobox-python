"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { 
  CheckCircle2, 
  XCircle, 
  Settings, 
  Plug, 
  AlertCircle,
  ArrowRight,
  Shield,
  Key,
  Link2,
  Webhook
} from "lucide-react"
import { useState } from "react"

export type IntegrationType = {
  id: string
  name: string
  description: string
  category: string
  icon?: string
  authMethod: "oauth2" | "api_key" | "webhook" | "basic_auth"
  status: "connected" | "disconnected" | "error" | "pending"
  capabilities?: string[]
  lastSync?: string
  errorMessage?: string
  availableTemplates?: number
  comingSoon?: boolean
}

interface IntegrationCardProps {
  integration: IntegrationType
  onConnect?: () => void
  onDisconnect?: () => void
  onSettings?: () => void
  onViewTemplates?: () => void
  compact?: boolean
}

const authMethodIcons = {
  oauth2: Shield,
  api_key: Key,
  webhook: Webhook,
  basic_auth: Link2
}

const statusConfig = {
  connected: {
    icon: CheckCircle2,
    color: "text-green-600",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
    label: "Connected"
  },
  disconnected: {
    icon: XCircle,
    color: "text-gray-400",
    bgColor: "bg-gray-50",
    borderColor: "border-gray-200",
    label: "Not Connected"
  },
  error: {
    icon: AlertCircle,
    color: "text-red-600",
    bgColor: "bg-red-50",
    borderColor: "border-red-200",
    label: "Error"
  },
  pending: {
    icon: Plug,
    color: "text-yellow-600",
    bgColor: "bg-yellow-50",
    borderColor: "border-yellow-200",
    label: "Pending"
  }
}

export function IntegrationCard({ 
  integration, 
  onConnect, 
  onSettings, 
  onViewTemplates,
  compact = false 
}: IntegrationCardProps) {
  const [isLoading, setIsLoading] = useState(false)
  const status = statusConfig[integration.status]
  const StatusIcon = status.icon
  const AuthIcon = authMethodIcons[integration.authMethod]

  const handleConnect = async () => {
    setIsLoading(true)
    try {
      await onConnect?.()
    } finally {
      setIsLoading(false)
    }
  }


  if (compact) {
    return (
      <Card className={cn(
        "hover:shadow-md transition-shadow min-w-[280px]",
        status.borderColor,
        integration.comingSoon && "opacity-75"
      )}>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className={cn("p-2 rounded-lg flex-shrink-0", status.bgColor)}>
                <StatusIcon className={cn("h-5 w-5", status.color)} />
              </div>
              <div className="flex-1 min-w-0">
                <CardTitle className="text-base truncate">{integration.name}</CardTitle>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <Badge variant="secondary" className="text-xs">
                    <AuthIcon className="h-3 w-3 mr-1" />
                    {integration.authMethod.replace("_", " ")}
                  </Badge>
                  {integration.availableTemplates && integration.availableTemplates > 0 && (
                    <Badge variant="outline" className="text-xs">
                      {integration.availableTemplates} templates
                    </Badge>
                  )}
                  {integration.comingSoon && (
                    <Badge variant="outline" className="text-xs">
                      Coming Soon
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            {!integration.comingSoon && (
              integration.status === "connected" ? (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={onSettings}
                  disabled={isLoading}
                  className="flex-shrink-0"
                >
                  <Settings className="h-4 w-4" />
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="default"
                  onClick={handleConnect}
                  disabled={isLoading}
                  className="flex-shrink-0"
                >
                  Connect
                </Button>
              )
            )}
          </div>
        </CardHeader>
      </Card>
    )
  }

  return (
    <Card className={cn(
      "hover:shadow-lg transition-shadow min-w-[300px] flex flex-col",
      status.borderColor,
      integration.comingSoon && "opacity-75"
    )}>
      <CardHeader className="flex-1">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={cn("p-3 rounded-lg", status.bgColor)}>
              <StatusIcon className={cn("h-6 w-6", status.color)} />
            </div>
            <div>
              <CardTitle>{integration.name}</CardTitle>
              <CardDescription className="mt-1">
                {integration.description}
              </CardDescription>
            </div>
          </div>
          <Badge 
            variant={integration.status === "connected" ? "default" : "secondary"}
            className="ml-2"
          >
            {status.label}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="text-xs">
            <AuthIcon className="h-3 w-3 mr-1" />
            {integration.authMethod.replace("_", " ").toUpperCase()}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {integration.category}
          </Badge>
          {integration.availableTemplates && integration.availableTemplates > 0 && (
            <Badge variant="secondary" className="text-xs">
              {integration.availableTemplates} action templates
            </Badge>
          )}
        </div>

        {integration.capabilities && integration.capabilities.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Capabilities</p>
            <div className="flex flex-wrap gap-1">
              {integration.capabilities.map((capability) => (
                <Badge key={capability} variant="secondary" className="text-xs">
                  {capability}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {integration.status === "error" && integration.errorMessage && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3">
            <p className="text-sm text-red-800">{integration.errorMessage}</p>
          </div>
        )}

        {integration.status === "connected" && integration.lastSync && (
          <div className="text-sm text-muted-foreground">
            Last synced: {new Date(integration.lastSync).toLocaleString()}
          </div>
        )}
      </CardContent>

      <CardFooter className="flex justify-between">
        {integration.comingSoon ? (
          <Button
            variant="outline"
            disabled
            className="w-full"
          >
            Coming Soon
          </Button>
        ) : integration.status === "connected" ? (
          <>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onSettings}
                disabled={isLoading}
              >
                <Settings className="h-4 w-4 mr-2" />
                Settings
              </Button>
            </div>
            {integration.availableTemplates && integration.availableTemplates > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onViewTemplates}
              >
                View Templates
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            )}
          </>
        ) : (
          <>
            <Button
              variant="default"
              onClick={handleConnect}
              disabled={isLoading}
            >
              <Plug className="h-4 w-4 mr-2" />
              Connect {integration.name}
            </Button>
            {integration.availableTemplates && integration.availableTemplates > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onViewTemplates}
              >
                {integration.availableTemplates} Templates
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            )}
          </>
        )}
      </CardFooter>
    </Card>
  )
}