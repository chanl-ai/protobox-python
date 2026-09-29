"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { cn } from "@/lib/utils"
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Info,
  Lock,
  Plug,
  Shield,
  TrendingUp,
  Zap,
} from "lucide-react"
import { IntegrationType } from "./integration-card"
import { ActionTemplate } from "./template-browser"

interface IntegrationDependencyCheckerProps {
  templates: ActionTemplate[]
  connectedIntegrations: IntegrationType[]
  onConnectIntegration: (integrationType: string) => void
  onViewTemplates?: (integrationType: string) => void
}

interface IntegrationStats {
  integrationType: string
  displayName: string
  isConnected: boolean
  enabledTemplates: number
  potentialTemplates: number
  requiredByTemplates: ActionTemplate[]
  optionalForTemplates: ActionTemplate[]
  totalValue: number // Calculated score based on template popularity
}

export function IntegrationDependencyChecker({
  templates,
  connectedIntegrations,
  onConnectIntegration,
  onViewTemplates,
}: IntegrationDependencyCheckerProps) {
  // Get connected integration types
  const connectedTypes = connectedIntegrations
    .filter(i => i.status === "connected")
    .map(i => i.id)

  // Calculate integration statistics
  const calculateIntegrationStats = (): IntegrationStats[] => {
    const statsMap = new Map<string, IntegrationStats>()

    // Initialize stats for all integration types mentioned in templates
    templates.forEach(template => {
      template.integrations.forEach(integration => {
        if (!statsMap.has(integration.integration_type)) {
          const connectedIntegration = connectedIntegrations.find(
            i => i.id === integration.integration_type
          )
          
          statsMap.set(integration.integration_type, {
            integrationType: integration.integration_type,
            displayName: connectedIntegration?.name || integration.integration_type,
            isConnected: connectedTypes.includes(integration.integration_type),
            enabledTemplates: 0,
            potentialTemplates: 0,
            requiredByTemplates: [],
            optionalForTemplates: [],
            totalValue: 0,
          })
        }

        const stats = statsMap.get(integration.integration_type)!
        
        if (integration.required) {
          stats.requiredByTemplates.push(template)
          stats.totalValue += template.popularity_score
        } else {
          stats.optionalForTemplates.push(template)
          stats.totalValue += template.popularity_score * 0.5 // Optional worth half
        }
      })
    })

    // Calculate enabled vs potential templates
    statsMap.forEach((stats, integrationType) => {
      if (stats.isConnected) {
        // Count templates that are fully enabled (all required integrations connected)
        stats.enabledTemplates = stats.requiredByTemplates.filter(template => {
          const requiredIntegrations = template.integrations.filter(i => i.required)
          return requiredIntegrations.every(i => connectedTypes.includes(i.integration_type))
        }).length
      }
      
      stats.potentialTemplates = stats.requiredByTemplates.length
    })

    return Array.from(statsMap.values()).sort((a, b) => {
      // Sort by: connected status, then total value
      if (a.isConnected !== b.isConnected) {
        return a.isConnected ? -1 : 1
      }
      return b.totalValue - a.totalValue
    })
  }

  const integrationStats = calculateIntegrationStats()

  // Calculate overall progress
  const totalPossibleTemplates = templates.length
  const currentlyEnabledTemplates = templates.filter(template => {
    const requiredIntegrations = template.integrations.filter(i => i.required)
    return requiredIntegrations.every(i => connectedTypes.includes(i.integration_type))
  }).length
  const progressPercentage = (currentlyEnabledTemplates / totalPossibleTemplates) * 100

  // Get top missing integrations (not connected but high value)
  const topMissingIntegrations = integrationStats
    .filter(stats => !stats.isConnected)
    .slice(0, 3)

  // Get integration recommendations
  const getRecommendations = () => {
    const recommendations = []
    
    // Find integrations that would unlock the most templates
    const highImpactIntegrations = integrationStats
      .filter(stats => !stats.isConnected && stats.potentialTemplates > 0)
      .sort((a, b) => b.potentialTemplates - a.potentialTemplates)
      .slice(0, 3)
    
    if (highImpactIntegrations.length > 0) {
      recommendations.push({
        title: "High Impact Integrations",
        description: "Connect these to unlock the most templates",
        integrations: highImpactIntegrations,
      })
    }

    // Find integrations with high popularity score
    const popularIntegrations = integrationStats
      .filter(stats => !stats.isConnected && stats.totalValue > 150)
      .sort((a, b) => b.totalValue - a.totalValue)
      .slice(0, 3)
    
    if (popularIntegrations.length > 0) {
      recommendations.push({
        title: "Popular Integrations",
        description: "Most requested by popular templates",
        integrations: popularIntegrations,
      })
    }

    return recommendations
  }

  const recommendations = getRecommendations()

  return (
    <div className="space-y-6">
      {/* Overall Progress Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Template Availability</CardTitle>
              <CardDescription>
                {currentlyEnabledTemplates} of {totalPossibleTemplates} templates available
              </CardDescription>
            </div>
            <div className="text-3xl font-bold text-primary">
              {Math.round(progressPercentage)}%
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Progress value={progressPercentage} className="h-2" />
          <div className="mt-4 flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>{connectedTypes.length} integrations connected</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-yellow-600" />
              <span>{currentlyEnabledTemplates} templates ready</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Connected</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{connectedTypes.length}</div>
            <p className="text-xs text-muted-foreground">integrations</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Available</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{currentlyEnabledTemplates}</div>
            <p className="text-xs text-muted-foreground">templates</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Potential</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {totalPossibleTemplates - currentlyEnabledTemplates}
            </div>
            <p className="text-xs text-muted-foreground">more templates</p>
          </CardContent>
        </Card>
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Recommended Integrations</h3>
          {recommendations.map((rec, index) => (
            <Card key={index}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-base">{rec.title}</CardTitle>
                    <CardDescription className="text-sm">
                      {rec.description}
                    </CardDescription>
                  </div>
                  <TrendingUp className="h-5 w-5 text-primary" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {rec.integrations.map(stats => (
                    <div
                      key={stats.integrationType}
                      className="flex items-center justify-between p-3 rounded-lg border"
                    >
                      <div className="flex-1">
                        <div className="font-medium">{stats.displayName}</div>
                        <div className="text-sm text-muted-foreground">
                          Unlocks {stats.potentialTemplates} template{stats.potentialTemplates !== 1 ? "s" : ""}
                          {stats.optionalForTemplates.length > 0 && 
                            ` • Enhances ${stats.optionalForTemplates.length} more`}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => onConnectIntegration(stats.integrationType)}
                      >
                        <Plug className="h-4 w-4 mr-2" />
                        Connect
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* All Integrations Status */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Integration Impact Analysis</h3>
        <div className="grid gap-4">
          {integrationStats.map(stats => (
            <Card
              key={stats.integrationType}
              className={cn(
                "transition-colors",
                stats.isConnected && "border-green-200 bg-green-50/50"
              )}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {stats.isConnected ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : (
                      <Shield className="h-5 w-5 text-gray-400" />
                    )}
                    <div>
                      <CardTitle className="text-base">{stats.displayName}</CardTitle>
                      <CardDescription className="text-sm">
                        {stats.isConnected ? (
                          <>
                            Enabling {stats.enabledTemplates} template{stats.enabledTemplates !== 1 ? "s" : ""}
                            {stats.optionalForTemplates.length > 0 && 
                              ` • Enhancing ${stats.optionalForTemplates.length} more`}
                          </>
                        ) : (
                          <>
                            Required by {stats.potentialTemplates} template{stats.potentialTemplates !== 1 ? "s" : ""}
                            {stats.optionalForTemplates.length > 0 && 
                              ` • Optional for ${stats.optionalForTemplates.length} more`}
                          </>
                        )}
                      </CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {stats.totalValue > 0 && (
                      <Badge variant="secondary">
                        Value: {Math.round(stats.totalValue)}
                      </Badge>
                    )}
                    {!stats.isConnected ? (
                      <Button
                        size="sm"
                        onClick={() => onConnectIntegration(stats.integrationType)}
                      >
                        Connect
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onViewTemplates?.(stats.integrationType)}
                      >
                        View Templates
                        <ArrowRight className="h-3 w-3 ml-1" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              
              {/* Show some example templates */}
              {stats.requiredByTemplates.length > 0 && (
                <CardContent>
                  <div className="space-y-2">
                    <Label className="text-xs text-muted-foreground">
                      {stats.isConnected ? "Enabled Templates" : "Would Enable"}
                    </Label>
                    <div className="flex flex-wrap gap-2">
                      {stats.requiredByTemplates.slice(0, 5).map(template => (
                        <Badge
                          key={template.id}
                          variant={stats.isConnected ? "default" : "outline"}
                          className="text-xs"
                        >
                          {template.name}
                        </Badge>
                      ))}
                      {stats.requiredByTemplates.length > 5 && (
                        <Badge variant="secondary" className="text-xs">
                          +{stats.requiredByTemplates.length - 5} more
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      </div>

      {/* Info Section */}
      <Card className="bg-blue-50/50 border-blue-200">
        <CardHeader>
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <CardTitle className="text-base">How Integration Dependencies Work</CardTitle>
              <CardDescription className="text-sm mt-1">
                Action templates may require one or more integrations to function. Connect the required
                integrations to unlock templates and enable powerful automations. Optional integrations
                add extra functionality but aren't required to use the template.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
      </Card>
    </div>
  )
}

// Fix missing Label import
import { Label } from "@/components/ui/label"