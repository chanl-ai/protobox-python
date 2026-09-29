// ProtoBox Embed Message Types and Interfaces

export interface ProtoBoxMessage<T = any> {
  type: string
  data?: T
  timestamp?: number
  version?: string
}

// Message types sent from iframe to parent
export const IFRAME_MESSAGES = {
  // Lifecycle events
  READY: 'protobox-ready',
  ERROR: 'protobox-error',
  
  // Integration events
  OAUTH_STARTING: 'protobox-oauth-starting',
  OAUTH_COMPLETED: 'protobox-oauth-completed',
  OAUTH_FAILED: 'protobox-oauth-failed',
  INTEGRATION_CONNECTED: 'protobox-integration-connected',
  INTEGRATION_DISCONNECTED: 'protobox-integration-disconnected',
  INTEGRATION_UPDATED: 'protobox-integration-updated',
  
  // User interactions
  SETTINGS_REQUESTED: 'protobox-settings-requested',
  INTEGRATION_SELECTED: 'protobox-integration-selected',
  
  // Navigation
  HEIGHT_CHANGED: 'protobox-height-changed',
  NAVIGATE: 'protobox-navigate',
} as const

// Message types sent from parent to iframe
export const PARENT_MESSAGES = {
  // Commands
  REFRESH: 'protobox-refresh',
  UPDATE_THEME: 'protobox-update-theme',
  UPDATE_USER: 'protobox-update-user',
  FILTER_INTEGRATIONS: 'protobox-filter-integrations',
  
  // Configuration
  SET_CONFIG: 'protobox-set-config',
  SET_CUSTOM_STYLES: 'protobox-set-custom-styles',
} as const

// Data interfaces
export interface Integration {
  id: string
  type: string
  name: string
  description: string
  icon?: string
  category?: string
  is_connected: boolean
  connected_at?: string
  status: 'connected' | 'disconnected' | 'error' | 'refreshing'
  metadata?: Record<string, any>
}

export interface OAuthStartData {
  integration: string
  scopes?: string[]
  state?: string
}

export interface OAuthCompleteData {
  integration: string
  success: boolean
  error?: string
  metadata?: Record<string, any>
}

export interface ErrorData {
  code: string
  message: string
  details?: any
}

export interface ReadyData {
  mode: 'demo' | 'sandbox' | 'production'
  integrations_count?: number
  features?: string[]
}

export interface HeightData {
  height: number
}

export interface NavigateData {
  path: string
  target?: '_blank' | '_self' | '_parent' | '_top'
}

export interface ConfigData {
  theme?: 'light' | 'dark' | 'auto'
  language?: string
  features?: {
    search?: boolean
    categories?: boolean
    bulk_actions?: boolean
  }
  custom_integrations?: Integration[]
}

export interface FilterData {
  categories?: string[]
  search?: string
  status?: ('connected' | 'disconnected')[]
  custom_filter?: (integration: Integration) => boolean
}

// Type guards
export function isProtoBoxMessage(message: any): message is ProtoBoxMessage {
  return message && typeof message.type === 'string'
}

export function isIframeMessage(type: string): boolean {
  return Object.values(IFRAME_MESSAGES).includes(type as any)
}

export function isParentMessage(type: string): boolean {
  return Object.values(PARENT_MESSAGES).includes(type as any)
}