"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Filter,
  Globe,
  Lock,
  Plus,
  Search,
  Settings,
  Shield,
  Star,
  Zap,
} from "lucide-react"
import { useState } from "react"
import { IntegrationType } from "./integration-card"

export interface ActionTemplate {
  id: string
  name: string
  description: string
  category: "productivity" | "communication" | "data" | "ai" | "finance" | "marketing"
  integrations: {
    integration_type: string
    required: boolean
  }[]
  popularity_score: number
  status: "active" | "beta" | "coming_soon"
  estimated_time?: string
  tags?: string[]
}

interface TemplateBrowserProps {
  templates: ActionTemplate[]
  connectedIntegrations: IntegrationType[]
  onSelectTemplate: (template: ActionTemplate) => void
  onConnectIntegration?: (integrationType: string) => void
}

export function TemplateBrowser({
  templates,
  connectedIntegrations,
  onSelectTemplate,
  onConnectIntegration,
}: TemplateBrowserProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategory, setSelectedCategory] = useState<string>("all")
  const [showOnlyAvailable, setShowOnlyAvailable] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<ActionTemplate | null>(null)
  const [showTemplateDetails, setShowTemplateDetails] = useState(false)

  // Get connected integration types
  const connectedTypes = connectedIntegrations
    .filter(i => i.status === "connected")
    .map(i => i.id)

  // Check if template is available
  const isTemplateAvailable = (template: ActionTemplate) => {
    const requiredIntegrations = template.integrations.filter(i => i.required)
    return requiredIntegrations.every(i => connectedTypes.includes(i.integration_type))
  }

  // Get missing integrations for a template
  const getMissingIntegrations = (template: ActionTemplate) => {
    return template.integrations
      .filter(i => i.required && !connectedTypes.includes(i.integration_type))
      .map(i => i.integration_type)
  }

  // Get optional integrations for a template
  const getOptionalIntegrations = (template: ActionTemplate) => {
    return template.integrations
      .filter(i => !i.required)
      .map(i => i.integration_type)
  }

  // Filter templates
  const filteredTemplates = templates.filter(template => {
    // Search filter
    if (searchQuery && !template.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !template.description.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }

    // Category filter
    if (selectedCategory !== "all" && template.category !== selectedCategory) {
      return false
    }

    // Availability filter
    if (showOnlyAvailable && !isTemplateAvailable(template)) {
      return false
    }

    return true
  })

  // Group templates by category
  const categories = [
    { id: "all", name: "All Templates", count: templates.length },
    { id: "productivity", name: "Productivity", count: templates.filter(t => t.category === "productivity").length },
    { id: "communication", name: "Communication", count: templates.filter(t => t.category === "communication").length },
    { id: "data", name: "Data & Analytics", count: templates.filter(t => t.category === "data").length },
    { id: "ai", name: "AI & Automation", count: templates.filter(t => t.category === "ai").length },
    { id: "finance", name: "Finance", count: templates.filter(t => t.category === "finance").length },
    { id: "marketing", name: "Marketing", count: templates.filter(t => t.category === "marketing").length },
  ]

  const handleSelectTemplate = (template: ActionTemplate) => {
    setSelectedTemplate(template)
    setShowTemplateDetails(true)
  }

  const handleUseTemplate = () => {
    if (selectedTemplate) {
      onSelectTemplate(selectedTemplate)
      setShowTemplateDetails(false)
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge variant="default">Active</Badge>
      case "beta":
        return <Badge variant="secondary">Beta</Badge>
      case "coming_soon":
        return <Badge variant="outline">Coming Soon</Badge>
      default:
        return null
    }
  }

  const getPopularityStars = (score: number) => {
    const stars = Math.round(score / 20) // Convert 0-100 to 0-5
    return (
      <div className="flex items-center gap-0.5">
        {[...Array(5)].map((_, i) => (
          <Star
            key={i}
            className={cn(
              "h-3 w-3",
              i < stars ? "fill-yellow-500 text-yellow-500" : "text-gray-300"
            )}
          />
        ))}
      </div>
    )
  }

  return (
    <>
      <div className="space-y-6">
        {/* Search and Filters */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant={showOnlyAvailable ? "default" : "outline"}
              size="sm"
              onClick={() => setShowOnlyAvailable(!showOnlyAvailable)}
            >
              <Filter className="h-4 w-4 mr-2" />
              Available Only
            </Button>
          </div>
        </div>

        {/* Category Tabs */}
        <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
          <TabsList className="w-full justify-start overflow-x-auto">
            {categories.map(category => (
              <TabsTrigger key={category.id} value={category.id}>
                {category.name}
                <Badge variant="secondary" className="ml-2">
                  {category.count}
                </Badge>
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        {/* Templates Grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredTemplates.map(template => {
            const available = isTemplateAvailable(template)
            const missing = getMissingIntegrations(template)
            const optional = getOptionalIntegrations(template)

            return (
              <Card
                key={template.id}
                className={cn(
                  "hover:shadow-md transition-shadow cursor-pointer",
                  !available && "opacity-75"
                )}
                onClick={() => handleSelectTemplate(template)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-base">{template.name}</CardTitle>
                      <div className="flex items-center gap-2">
                        {getStatusBadge(template.status)}
                        {getPopularityStars(template.popularity_score)}
                      </div>
                    </div>
                    {available ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : missing.length > 0 ? (
                      <AlertCircle className="h-5 w-5 text-yellow-600" />
                    ) : (
                      <Lock className="h-5 w-5 text-gray-400" />
                    )}
                  </div>
                  <CardDescription className="text-sm mt-2">
                    {template.description}
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-3">
                  {/* Required Integrations */}
                  {template.integrations.filter(i => i.required).length > 0 && (
                    <div className="space-y-1">
                      <Label className="text-xs">Required</Label>
                      <div className="flex flex-wrap gap-1">
                        {template.integrations
                          .filter(i => i.required)
                          .map(integration => (
                            <Badge
                              key={integration.integration_type}
                              variant={
                                connectedTypes.includes(integration.integration_type)
                                  ? "default"
                                  : "outline"
                              }
                              className="text-xs"
                            >
                              {integration.integration_type}
                            </Badge>
                          ))}
                      </div>
                    </div>
                  )}

                  {/* Optional Integrations */}
                  {optional.length > 0 && (
                    <div className="space-y-1">
                      <Label className="text-xs text-muted-foreground">Optional</Label>
                      <div className="flex flex-wrap gap-1">
                        {optional.map(type => (
                          <Badge
                            key={type}
                            variant="secondary"
                            className="text-xs"
                          >
                            {type}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Tags */}
                  {template.tags && template.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {template.tags.map(tag => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* Estimated Time */}
                  {template.estimated_time && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {template.estimated_time} to set up
                    </div>
                  )}
                </CardContent>

                <CardFooter>
                  {available ? (
                    <Button size="sm" className="w-full">
                      <Plus className="h-4 w-4 mr-2" />
                      Use Template
                    </Button>
                  ) : missing.length > 0 ? (
                    <Button size="sm" variant="outline" className="w-full">
                      <Shield className="h-4 w-4 mr-2" />
                      {missing.length} Integration{missing.length > 1 ? "s" : ""} Needed
                    </Button>
                  ) : (
                    <Button size="sm" variant="outline" disabled className="w-full">
                      Coming Soon
                    </Button>
                  )}
                </CardFooter>
              </Card>
            )
          })}
        </div>

        {/* Empty State */}
        {filteredTemplates.length === 0 && (
          <div className="text-center py-12">
            <Zap className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">No templates found</h3>
            <p className="text-muted-foreground">
              Try adjusting your search or filters to find templates.
            </p>
          </div>
        )}
      </div>

      {/* Template Details Dialog */}
      <Dialog open={showTemplateDetails} onOpenChange={setShowTemplateDetails}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{selectedTemplate?.name}</DialogTitle>
            <DialogDescription>
              {selectedTemplate?.description}
            </DialogDescription>
          </DialogHeader>

          {selectedTemplate && (
            <div className="space-y-4">
              {/* Status and Popularity */}
              <div className="flex items-center gap-4">
                {getStatusBadge(selectedTemplate.status)}
                {getPopularityStars(selectedTemplate.popularity_score)}
                {selectedTemplate.estimated_time && (
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    {selectedTemplate.estimated_time}
                  </div>
                )}
              </div>

              {/* Integration Requirements */}
              <div className="space-y-3">
                <h4 className="font-medium">Integration Requirements</h4>
                
                {selectedTemplate.integrations.filter(i => i.required).length > 0 && (
                  <div className="space-y-2">
                    <Label>Required Integrations</Label>
                    <div className="space-y-2">
                      {selectedTemplate.integrations
                        .filter(i => i.required)
                        .map(integration => {
                          const isConnected = connectedTypes.includes(integration.integration_type)
                          return (
                            <div
                              key={integration.integration_type}
                              className="flex items-center justify-between p-2 rounded-lg border"
                            >
                              <span className="text-sm">{integration.integration_type}</span>
                              {isConnected ? (
                                <Badge variant="default">
                                  <CheckCircle2 className="h-3 w-3 mr-1" />
                                  Connected
                                </Badge>
                              ) : (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => onConnectIntegration?.(integration.integration_type)}
                                >
                                  Connect
                                  <ArrowRight className="h-3 w-3 ml-1" />
                                </Button>
                              )}
                            </div>
                          )
                        })}
                    </div>
                  </div>
                )}

                {getOptionalIntegrations(selectedTemplate).length > 0 && (
                  <div className="space-y-2">
                    <Label className="text-muted-foreground">Optional Integrations</Label>
                    <div className="flex flex-wrap gap-2">
                      {getOptionalIntegrations(selectedTemplate).map(type => (
                        <Badge key={type} variant="secondary">
                          {type}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Tags */}
              {selectedTemplate.tags && selectedTemplate.tags.length > 0 && (
                <div className="space-y-2">
                  <Label>Tags</Label>
                  <div className="flex flex-wrap gap-2">
                    {selectedTemplate.tags.map(tag => (
                      <Badge key={tag} variant="outline">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTemplateDetails(false)}>
              Cancel
            </Button>
            {selectedTemplate && isTemplateAvailable(selectedTemplate) ? (
              <Button onClick={handleUseTemplate}>
                <Plus className="h-4 w-4 mr-2" />
                Use This Template
              </Button>
            ) : (
              <Button disabled>
                <Lock className="h-4 w-4 mr-2" />
                Missing Required Integrations
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}