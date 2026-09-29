// Example usage of the new integration components
// This file demonstrates how to use the integration components together

"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  IntegrationCard,
  IntegrationSettingsDialog,
  TemplateBrowser,
  IntegrationDependencyChecker,
  type IntegrationType,
  type ActionTemplate,
} from "@/components/integrations"

// Example data - in real usage, this would come from your API
const mockIntegrations: IntegrationType[] = [
  {
    id: "google_calendar",
    name: "Google Calendar",
    description: "Schedule and manage calendar events",
    category: "productivity",
    authMethod: "oauth2",
    status: "connected",
    capabilities: ["calendar.events", "calendar.readonly"],
    lastSync: new Date().toISOString(),
    availableTemplates: 5,
  },
  {
    id: "slack",
    name: "Slack",
    description: "Team communication and messaging",
    category: "communication",
    authMethod: "oauth2",
    status: "disconnected",
    capabilities: ["messages.write", "channels.read"],
    availableTemplates: 8,
  },
  {
    id: "openai",
    name: "OpenAI",
    description: "AI-powered text generation and analysis",
    category: "ai",
    authMethod: "api_key",
    status: "disconnected",
    capabilities: ["completions", "embeddings"],
    availableTemplates: 12,
  },
  {
    id: "stripe",
    name: "Stripe",
    description: "Payment processing and billing",
    category: "finance",
    authMethod: "api_key",
    status: "connected",
    capabilities: ["payments", "subscriptions", "invoices"],
    lastSync: new Date().toISOString(),
    availableTemplates: 6,
  },
  {
    id: "github",
    name: "GitHub",
    description: "Code repository and project management",
    category: "development",
    authMethod: "oauth2",
    status: "disconnected",
    capabilities: ["repos", "issues", "pull_requests"],
    availableTemplates: 10,
  },
  {
    id: "hubspot",
    name: "HubSpot",
    description: "CRM and marketing automation",
    category: "crm",
    authMethod: "oauth2",
    status: "disconnected",
    capabilities: ["contacts", "deals", "marketing"],
    availableTemplates: 15,
  },
  {
    id: "gmail",
    name: "Gmail",
    description: "Email management and automation",
    category: "communication",
    authMethod: "oauth2",
    status: "disconnected",
    capabilities: ["send", "read", "labels"],
    availableTemplates: 7,
  },
  {
    id: "twilio",
    name: "Twilio",
    description: "SMS and voice communication",
    category: "communication",
    authMethod: "api_key",
    status: "disconnected",
    capabilities: ["sms", "voice", "whatsapp"],
    availableTemplates: 5,
  },
  {
    id: "sendgrid",
    name: "SendGrid",
    description: "Email delivery and marketing",
    category: "communication",
    authMethod: "api_key",
    status: "disconnected",
    capabilities: ["transactional", "marketing", "analytics"],
    availableTemplates: 4,
  },
  {
    id: "microsoft_365",
    name: "Microsoft 365",
    description: "Office productivity suite integration",
    category: "productivity",
    authMethod: "oauth2",
    status: "disconnected",
    capabilities: ["calendar", "mail", "onedrive", "teams"],
    availableTemplates: 8,
  },
  {
    id: "notion",
    name: "Notion",
    description: "Workspace and knowledge management",
    category: "productivity",
    authMethod: "api_key",
    status: "disconnected",
    capabilities: ["pages", "databases", "blocks"],
    availableTemplates: 6,
  },
  {
    id: "shopify",
    name: "Shopify",
    description: "E-commerce platform integration",
    category: "ecommerce",
    authMethod: "oauth2",
    status: "disconnected",
    capabilities: ["orders", "products", "customers"],
    availableTemplates: 9,
    comingSoon: true,
  },
  {
    id: "salesforce",
    name: "Salesforce",
    description: "Enterprise CRM platform",
    category: "crm",
    authMethod: "oauth2",
    status: "disconnected",
    capabilities: ["leads", "opportunities", "accounts"],
    availableTemplates: 12,
    comingSoon: true,
  },
  {
    id: "linkedin",
    name: "LinkedIn",
    description: "Professional networking and recruitment",
    category: "social",
    authMethod: "oauth2",
    status: "disconnected",
    capabilities: ["profile", "connections", "messaging"],
    availableTemplates: 4,
    comingSoon: true,
  },
]

const mockTemplates: ActionTemplate[] = [
  {
    id: "calendar_scheduling",
    name: "Smart Calendar Scheduling",
    description: "AI-powered appointment scheduling with availability checking",
    category: "productivity",
    integrations: [
      { integration_type: "google_calendar", required: true },
      { integration_type: "openai", required: false },
    ],
    popularity_score: 85,
    status: "active",
    estimated_time: "5 minutes",
    tags: ["scheduling", "calendar", "automation"],
  },
  {
    id: "slack_notifications",
    name: "Smart Slack Notifications",
    description: "Send intelligent notifications to Slack channels",
    category: "communication",
    integrations: [
      { integration_type: "slack", required: true },
      { integration_type: "openai", required: false },
    ],
    popularity_score: 75,
    status: "active",
    estimated_time: "3 minutes",
    tags: ["notifications", "slack", "messaging"],
  },
  {
    id: "payment_processor",
    name: "AI Payment Assistant",
    description: "Process payments with intelligent fraud detection",
    category: "finance",
    integrations: [
      { integration_type: "stripe", required: true },
      { integration_type: "openai", required: true },
    ],
    popularity_score: 90,
    status: "active",
    estimated_time: "10 minutes",
    tags: ["payments", "stripe", "ai"],
  },
  {
    id: "customer_support",
    name: "AI Customer Support",
    description: "Automated customer support with Slack and AI",
    category: "communication",
    integrations: [
      { integration_type: "slack", required: true },
      { integration_type: "openai", required: true },
      { integration_type: "stripe", required: false },
    ],
    popularity_score: 95,
    status: "beta",
    estimated_time: "15 minutes",
    tags: ["support", "ai", "automation"],
  },
]

export function IntegrationsExamplePage() {
  const [selectedIntegration, setSelectedIntegration] = useState<IntegrationType | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("integrations")

  const handleConnect = (integrationId: string) => {
    console.log("Connecting integration:", integrationId)
    // In real usage, this would call your API to start OAuth flow or show API key input
  }

  const handleDisconnect = (integrationId: string) => {
    console.log("Disconnecting integration:", integrationId)
    // In real usage, this would call your API to disconnect the integration
  }

  const handleSettings = (integration: IntegrationType) => {
    setSelectedIntegration(integration)
    setSettingsOpen(true)
  }

  const handleSelectTemplate = (template: ActionTemplate) => {
    console.log("Selected template:", template)
    // In real usage, this would navigate to action creation with the template
  }

  const handleViewTemplates = (integrationType: string) => {
    console.log("View templates for:", integrationType)
    setActiveTab("templates")
    // You could also filter templates by this integration type
  }

  return (
    <div className="container mx-auto py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">Integrations & Templates</h1>
        <p className="text-muted-foreground">
          Connect your tools and unlock powerful automation templates
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="dependencies">Dependencies</TabsTrigger>
          <TabsTrigger value="compact">Compact View</TabsTrigger>
        </TabsList>

        <TabsContent value="integrations" className="space-y-6">
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 auto-rows-fr">
            {mockIntegrations.map((integration) => (
              <IntegrationCard
                key={integration.id}
                integration={integration}
                onConnect={() => handleConnect(integration.id)}
                onDisconnect={() => handleDisconnect(integration.id)}
                onSettings={() => handleSettings(integration)}
                onViewTemplates={() => handleViewTemplates(integration.id)}
              />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="templates" className="space-y-6">
          <TemplateBrowser
            templates={mockTemplates}
            connectedIntegrations={mockIntegrations}
            onSelectTemplate={handleSelectTemplate}
            onConnectIntegration={handleConnect}
          />
        </TabsContent>

        <TabsContent value="dependencies" className="space-y-6">
          <IntegrationDependencyChecker
            templates={mockTemplates}
            connectedIntegrations={mockIntegrations}
            onConnectIntegration={handleConnect}
            onViewTemplates={handleViewTemplates}
          />
        </TabsContent>

        <TabsContent value="compact" className="space-y-6">
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 auto-rows-fr">
            {mockIntegrations.map((integration) => (
              <IntegrationCard
                key={integration.id}
                integration={integration}
                onConnect={() => handleConnect(integration.id)}
                onDisconnect={() => handleDisconnect(integration.id)}
                onSettings={() => handleSettings(integration)}
                onViewTemplates={() => handleViewTemplates(integration.id)}
                compact
              />
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Settings Dialog */}
      <IntegrationSettingsDialog
        integration={selectedIntegration}
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        onSave={(settings) => {
          console.log("Saving settings:", settings)
          setSettingsOpen(false)
        }}
        onDisconnect={() => {
          if (selectedIntegration) {
            handleDisconnect(selectedIntegration.id)
            setSettingsOpen(false)
          }
        }}
        onTestConnection={async () => {
          // In real usage, this would test the connection
          console.log("Testing connection...")
          return true
        }}
        onRefreshToken={async () => {
          // In real usage, this would refresh OAuth token
          console.log("Refreshing token...")
        }}
      />
    </div>
  )
}