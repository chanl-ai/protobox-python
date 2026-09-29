// Integration Icons Configuration
// This file manages all integration icons in a centralized way

// Icon types
export interface IntegrationIcon {
  type: 'svg' | 'image' | 'component'
  content: string | React.ComponentType<any>
  color?: string
  className?: string
}

// Icon registry - add new icons here
export const INTEGRATION_ICONS: Record<string, IntegrationIcon> = {
  // Google Services
  'google_calendar': {
    type: 'image',
    content: '/icons/integrations/google_calendar.svg',
    color: '#4285F4'
  },
  'google_gmail': {
    type: 'image',
    content: '/icons/integrations/google_gmail.svg',
    color: '#EA4335'
  },
  'google_drive': {
    type: 'image',
    content: '/icons/integrations/google_drive.svg',
    color: '#4285F4'
  },
  'google_sheets': {
    type: 'image',
    content: '/icons/integrations/google_sheets.svg',
    color: '#0F9D58'
  },
  'google_docs': {
    type: 'image',
    content: '/icons/integrations/google_docs.svg',
    color: '#4285F4'
  },
  'google_analytics': {
    type: 'image',
    content: '/icons/integrations/google_analytics.svg',
    color: '#F4B400'
  },
  'google_ads': {
    type: 'image',
    content: '/icons/integrations/google_ads.svg',
    color: '#EA4335'
  },

  // Communication
  'slack': {
    type: 'image',
    content: '/icons/integrations/slack.svg',
    color: '#4A154B'
  },
  'twilio': {
    type: 'image',
    content: '/icons/integrations/twilio.svg',
    color: '#F22F46'
  },
  'sendgrid': {
    type: 'image',
    content: '/icons/integrations/sendgrid.svg',
    color: '#00C4B3'
  },
  'resend': {
    type: 'image',
    content: '/icons/integrations/resend.svg',
    color: '#3A82EE'
  },

  // AI & Development
  'openai': {
    type: 'image',
    content: '/icons/integrations/openai.svg',
    color: '#10A37F'
  },
  'anthropic': {
    type: 'image',
    content: '/icons/integrations/anthropic.svg',
    color: '#D97706'
  },
  'github': {
    type: 'image',
    content: '/icons/integrations/github.svg',
    color: '#181717'
  },

  // Business & Productivity
  'stripe': {
    type: 'image',
    content: '/icons/integrations/stripe.svg',
    color: '#6772E5'
  },
  'notion': {
    type: 'image',
    content: '/icons/integrations/notion.svg',
    color: '#000000'
  },
  'airtable': {
    type: 'image',
    content: '/icons/integrations/airtable.svg',
    color: '#18BFFF'
  },
  'hubspot': {
    type: 'image',
    content: '/icons/integrations/hubspot.svg',
    color: '#FF7A59'
  },
  'shopify': {
    type: 'image',
    content: '/icons/integrations/shopify.svg',
    color: '#95BF47'
  },
  'salesforce': {
    type: 'image',
    content: '/icons/integrations/salesforce.svg',
    color: '#00A1E0'
  }
}

// Helper function to get an icon
export function getIntegrationIcon(integrationId: string): IntegrationIcon | null {
  return INTEGRATION_ICONS[integrationId] || null
}

// Helper function to get all available icon IDs
export function getAvailableIconIds(): string[] {
  return Object.keys(INTEGRATION_ICONS)
}

// Helper function to check if an icon exists
export function hasIntegrationIcon(integrationId: string): boolean {
  return integrationId in INTEGRATION_ICONS
}
