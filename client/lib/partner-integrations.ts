// Partner-specific integration configuration and filtering

export interface PartnerIntegrationConfig {
  partnerId: string
  integrationId: string
  enabled: boolean
  displayName?: string
  description?: string
  category?: string
  priority?: number
  customFields?: Record<string, any>
  permissions?: {
    connect: boolean
    disconnect: boolean
    configure: boolean
  }
  branding?: {
    logo?: string
    primaryColor?: string
    helpUrl?: string
  }
}

export interface PartnerProfile {
  partnerId: string
  name: string
  industry?: string
  tier: 'free' | 'pro' | 'enterprise'
  features: string[]
  allowedIntegrations?: string[]
  customBranding?: {
    primaryColor?: string
    logo?: string
  }
}

// Mock partner profiles - in production, this would come from database
const PARTNER_PROFILES: Record<string, PartnerProfile> = {
  'test_partner_dev': {
    partnerId: 'test_partner_dev',
    name: 'Test Partner',
    industry: 'software',
    tier: 'enterprise',
    features: ['oauth', 'webhooks', 'custom_fields', 'priority_support'],
    allowedIntegrations: ['google_calendar', 'hubspot', 'slack', 'stripe'],
    customBranding: {
      primaryColor: '#3b82f6'
    }
  },
  'demo_partner': {
    partnerId: 'demo_partner',
    name: 'Demo Partner',
    industry: 'generic',
    tier: 'free',
    features: ['oauth'],
    allowedIntegrations: ['google_calendar', 'slack']
  },
  'ecommerce_partner': {
    partnerId: 'ecommerce_partner',
    name: 'E-commerce Partner',
    industry: 'ecommerce',
    tier: 'pro',
    features: ['oauth', 'webhooks'],
    allowedIntegrations: ['shopify', 'stripe', 'hubspot', 'google_calendar']
  },
  'crm_partner': {
    partnerId: 'crm_partner',
    name: 'CRM Partner',
    industry: 'sales',
    tier: 'pro',
    features: ['oauth', 'webhooks'],
    allowedIntegrations: ['hubspot', 'salesforce', 'google_calendar', 'slack']
  }
}

// Integration configuration per partner
const PARTNER_INTEGRATION_CONFIGS: Record<string, PartnerIntegrationConfig[]> = {
  'test_partner_dev': [
    {
      partnerId: 'test_partner_dev',
      integrationId: 'google_calendar',
      enabled: true,
      displayName: 'Calendar Integration',
      description: 'Schedule meetings and manage your calendar',
      category: 'productivity',
      priority: 1,
      permissions: { connect: true, disconnect: true, configure: true }
    },
    {
      partnerId: 'test_partner_dev',
      integrationId: 'hubspot',
      enabled: true,
      displayName: 'CRM Integration',
      description: 'Sync contacts and manage your sales pipeline',
      category: 'crm',
      priority: 2,
      permissions: { connect: true, disconnect: true, configure: true }
    },
    {
      partnerId: 'test_partner_dev',
      integrationId: 'slack',
      enabled: true,
      priority: 3,
      permissions: { connect: true, disconnect: true, configure: false }
    },
    {
      partnerId: 'test_partner_dev',
      integrationId: 'stripe',
      enabled: true,
      priority: 4,
      permissions: { connect: true, disconnect: false, configure: true }
    }
  ],
  'ecommerce_partner': [
    {
      partnerId: 'ecommerce_partner',
      integrationId: 'shopify',
      enabled: true,
      displayName: 'Store Management',
      description: 'Manage your Shopify store and orders',
      category: 'ecommerce',
      priority: 1,
      permissions: { connect: true, disconnect: true, configure: true }
    },
    {
      partnerId: 'ecommerce_partner',
      integrationId: 'stripe',
      enabled: true,
      displayName: 'Payment Processing',
      description: 'Handle payments and subscriptions',
      category: 'payments',
      priority: 2,
      permissions: { connect: true, disconnect: true, configure: true }
    }
  ]
}

export class PartnerIntegrationFilter {
  private partnerId: string
  private profile: PartnerProfile | null = null

  constructor(partnerId: string) {
    this.partnerId = partnerId
    this.profile = PARTNER_PROFILES[partnerId] || null
  }

  /**
   * Get partner profile
   */
  getPartnerProfile(): PartnerProfile | null {
    return this.profile
  }

  /**
   * Filter integrations based on partner configuration
   */
  filterIntegrations(allIntegrations: any[]): any[] {
    if (!this.profile) {
      // No partner profile found, return all integrations
      return allIntegrations
    }

    const partnerConfigs = PARTNER_INTEGRATION_CONFIGS[this.partnerId] || []
    const allowedIntegrations = this.profile.allowedIntegrations || []

    return allIntegrations
      .filter(integration => {
        // Check if integration is allowed for this partner
        if (allowedIntegrations.length > 0) {
          return allowedIntegrations.includes(integration.type || integration.id)
        }
        return true
      })
      .map(integration => {
        // Apply partner-specific customization
        const config = partnerConfigs.find(c => 
          c.integrationId === (integration.type || integration.id)
        )

        if (config) {
          return {
            ...integration,
            name: config.displayName || integration.name,
            description: config.description || integration.description,
            category: config.category || integration.category,
            priority: config.priority || 999,
            permissions: config.permissions || {
              connect: true,
              disconnect: true, 
              configure: true
            },
            customFields: config.customFields || {},
            branding: config.branding || {}
          }
        }

        return integration
      })
      .sort((a, b) => (a.priority || 999) - (b.priority || 999))
  }

  /**
   * Check if partner has access to specific integration
   */
  hasIntegrationAccess(integrationId: string): boolean {
    if (!this.profile?.allowedIntegrations) {
      return true // No restrictions
    }
    return this.profile.allowedIntegrations.includes(integrationId)
  }

  /**
   * Check if partner has specific feature
   */
  hasFeature(feature: string): boolean {
    if (!this.profile) return false
    return this.profile.features.includes(feature)
  }

  /**
   * Get partner-specific categories
   */
  getCategories(integrations: any[]): Array<{id: string, name: string, count: number}> {
    const categoryMap = new Map<string, number>()
    
    integrations.forEach(integration => {
      const category = integration.category || 'other'
      categoryMap.set(category, (categoryMap.get(category) || 0) + 1)
    })

    const categories = [
      { id: 'all', name: 'All', count: integrations.length }
    ]

    // Add categories based on partner industry
    if (this.profile?.industry === 'ecommerce') {
      categories.push(
        { id: 'ecommerce', name: 'E-commerce', count: categoryMap.get('ecommerce') || 0 },
        { id: 'payments', name: 'Payments', count: categoryMap.get('payments') || 0 }
      )
    } else if (this.profile?.industry === 'sales') {
      categories.push(
        { id: 'crm', name: 'CRM', count: categoryMap.get('crm') || 0 }
      )
    }

    // Always add common categories if they have integrations
    const commonCategories = [
      { id: 'productivity', name: 'Productivity' },
      { id: 'communication', name: 'Communication' },
      { id: 'crm', name: 'CRM' },
      { id: 'finance', name: 'Finance' }
    ]

    commonCategories.forEach(cat => {
      if (categoryMap.has(cat.id) && !categories.find(c => c.id === cat.id)) {
        categories.push({
          id: cat.id,
          name: cat.name,
          count: categoryMap.get(cat.id) || 0
        })
      }
    })

    return categories.filter(cat => cat.count > 0 || cat.id === 'all')
  }

  /**
   * Get integration permissions for partner
   */
  getIntegrationPermissions(integrationId: string): {
    connect: boolean
    disconnect: boolean
    configure: boolean
  } {
    const config = PARTNER_INTEGRATION_CONFIGS[this.partnerId]?.find(
      c => c.integrationId === integrationId
    )

    return config?.permissions || {
      connect: true,
      disconnect: true,
      configure: true
    }
  }

  /**
   * Get partner branding
   */
  getBranding(): { primaryColor?: string; logo?: string } {
    return this.profile?.customBranding || {}
  }
}

// API functions that would typically fetch from backend
export async function getPartnerIntegrations(partnerId: string, userId?: string) {
  // In production, this would call: GET /api/partners/{partnerId}/integrations
  // and include user-specific connection status
  
  // Mock delay
  await new Promise(resolve => setTimeout(resolve, 500))
  
  // Mock data - would come from API
  const mockIntegrations = [
    {
      id: "1",
      type: "google_calendar",
      name: "Google Calendar",
      description: "Schedule meetings and manage events",
      category: "productivity",
      is_connected: false,
      status: "disconnected" as const
    },
    {
      id: "2", 
      type: "hubspot",
      name: "HubSpot",
      description: "CRM and marketing automation",
      category: "crm",
      is_connected: false,
      status: "disconnected" as const
    },
    {
      id: "3",
      type: "slack", 
      name: "Slack",
      description: "Team communication and notifications",
      category: "communication",
      is_connected: false,
      status: "disconnected" as const
    },
    {
      id: "4",
      type: "shopify",
      name: "Shopify", 
      description: "E-commerce platform integration",
      category: "ecommerce",
      is_connected: false,
      status: "disconnected" as const
    },
    {
      id: "5", 
      type: "stripe",
      name: "Stripe",
      description: "Payment processing and subscriptions", 
      category: "payments",
      is_connected: false,
      status: "disconnected" as const
    }
  ]

  // Filter based on partner configuration
  const filter = new PartnerIntegrationFilter(partnerId)
  return filter.filterIntegrations(mockIntegrations)
}