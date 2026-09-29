// Partner API client for embed integrations

export interface PartnerAPIConfig {
  baseUrl: string
  partnerId: string
  userId: string
  apiKey?: string
  timeout?: number
}

export interface PartnerIntegration {
  id: string
  integration_type: string
  display_name: string
  description: string
  category: string
  status: 'connected' | 'disconnected' | 'error' | 'setup'
  is_connected: boolean
  connected_at?: string
  error_message?: string
  available_actions?: Array<{
    id: string
    name: string
    description: string
  }>
  permissions?: {
    connect: boolean
    disconnect: boolean
    configure: boolean
  }
}

export interface PartnerUser {
  id: string
  email?: string
  name?: string
  partner_id: string
  created_at: string
  metadata?: Record<string, any>
}

export interface OAuthResponse {
  authorization_url?: string
  setup_required?: boolean
  instructions?: string
  success?: boolean
  error?: string
}

export class PartnerAPIClient {
  private config: PartnerAPIConfig
  private authToken?: string

  constructor(config: PartnerAPIConfig) {
    this.config = {
      timeout: 10000,
      ...config
    }
  }

  /**
   * Set authentication token
   */
  setAuthToken(token: string) {
    this.authToken = token
  }

  /**
   * Make authenticated API request
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<{ data?: T; error?: string }> {
    const url = `${this.config.baseUrl}${endpoint}`
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Partner-ID': this.config.partnerId,
      'X-User-ID': this.config.userId,
      ...((options.headers as Record<string, string>) || {})
    }

    // Add authentication
    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`
    } else if (this.config.apiKey) {
      headers['X-API-Key'] = this.config.apiKey
    }

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), this.config.timeout)

      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorText = await response.text()
        return { 
          error: `API request failed: ${response.status} ${response.statusText} - ${errorText}` 
        }
      }

      const data = await response.json()
      return { data }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        return { error: 'Request timeout' }
      }
      return { error: error.message || 'Network error' }
    }
  }

  /**
   * Get available integrations for partner
   */
  async getAvailableIntegrations(): Promise<{ data?: PartnerIntegration[]; error?: string }> {
    const params = new URLSearchParams({
      partner_id: this.config.partnerId,
      user_id: this.config.userId
    })
    return this.request<PartnerIntegration[]>(`/admin/api/v1/partners/integrations/available?${params}`)
  }

  /**
   * Get connected integrations for user
   */
  async getConnectedIntegrations(): Promise<{ data?: PartnerIntegration[]; error?: string }> {
    return this.request<PartnerIntegration[]>('/admin/api/v1/partners/integrations/connected')
  }

  /**
   * Start integration connection (OAuth flow)
   */
  async connectIntegration(integrationType: string): Promise<{ data?: OAuthResponse; error?: string }> {
    const params = new URLSearchParams({
      partner_id: this.config.partnerId,
      user_id: this.config.userId
    })
    return this.request<OAuthResponse>(`/admin/api/v1/partners/integrations/${integrationType}/connect?${params}`, {
      method: 'GET'
    })
  }

  /**
   * Disconnect integration
   */
  async disconnectIntegration(integrationType: string): Promise<{ data?: { success: boolean }; error?: string }> {
    const params = new URLSearchParams({
      partner_id: this.config.partnerId,
      user_id: this.config.userId
    })
    return this.request<{ success: boolean }>(`/admin/api/v1/partners/integrations/${integrationType}/disconnect?${params}`, {
      method: 'GET'
    })
  }

  /**
   * Get integration status
   */
  async getIntegrationStatus(integrationType: string): Promise<{ data?: PartnerIntegration; error?: string }> {
    const params = new URLSearchParams({
      partner_id: this.config.partnerId,
      user_id: this.config.userId
    })
    return this.request<PartnerIntegration>(`/admin/api/v1/partners/integrations/${integrationType}/status?${params}`)
  }

  /**
   * Test integration connection
   */
  async testIntegration(integrationType: string): Promise<{ data?: { success: boolean; message?: string }; error?: string }> {
    return this.request<{ success: boolean; message?: string }>(`/admin/api/v1/partners/integrations/${integrationType}/test`, {
      method: 'POST'
    })
  }

  /**
   * Get user profile
   */
  async getUserProfile(): Promise<{ data?: PartnerUser; error?: string }> {
    return this.request<PartnerUser>('/admin/api/v1/partners/users/profile')
  }

  /**
   * Create or update user
   */
  async upsertUser(userData: {
    email?: string
    name?: string
    metadata?: Record<string, any>
  }): Promise<{ data?: PartnerUser; error?: string }> {
    return this.request<PartnerUser>('/admin/api/v1/partners/users/upsert', {
      method: 'POST',
      body: JSON.stringify(userData)
    })
  }

  /**
   * Validate partner access
   */
  async validateAccess(): Promise<{ data?: { valid: boolean; partner: any }; error?: string }> {
    const params = new URLSearchParams({
      partner_id: this.config.partnerId,
      user_id: this.config.userId
    })
    return this.request<{ valid: boolean; partner: any }>(`/admin/api/v1/partners/validate?${params}`)
  }
}

// Utility function to create API client based on environment
export function createPartnerAPIClient(partnerId: string, userId: string): PartnerAPIClient {
  const baseUrl = process.env.NODE_ENV === 'development'
    ? 'http://localhost:8090'
    : 'http://localhost:8090'

  return new PartnerAPIClient({
    baseUrl,
    partnerId,
    userId,
    timeout: 15000 // Longer timeout for OAuth flows
  })
}

// Mock API client for testing
export class MockPartnerAPIClient extends PartnerAPIClient {
  private mockData: Record<string, any> = {}

  constructor(partnerId: string, userId: string) {
    super({
      baseUrl: 'http://localhost:8090', // Use real URL but override methods
      partnerId,
      userId
    })
  }

  // Override the request method to return mock data
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<{ data?: T; error?: string }> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 300))

    // Return mock data based on endpoint
    if (endpoint.includes('/validate')) {
      return {
        data: {
          valid: true,
          partner_id: this.config.partnerId,
          user_id: this.config.userId,
          is_demo: true,
          mode: 'demo'
        } as any
      }
    }

    if (endpoint.includes('/integrations/available')) {
      return {
        data: [
          {
            id: 'google_calendar',
            integration_type: 'google_calendar',
            display_name: 'Google Calendar',
            description: 'Schedule meetings and manage events',
            category: 'calendar',
            status: 'disconnected',
            is_connected: false,
            permissions: ['calendar.read', 'calendar.write']
          },
          {
            id: 'slack',
            integration_type: 'slack',
            display_name: 'Slack',
            description: 'Team communication and notifications',
            category: 'communication',
            status: 'disconnected',
            is_connected: false,
            permissions: ['messages.write', 'channels.read']
          },
          {
            id: 'stripe',
            integration_type: 'stripe',
            display_name: 'Stripe',
            description: 'Payment processing and subscriptions',
            category: 'payments',
            status: 'disconnected',
            is_connected: false,
            permissions: ['payments.read', 'subscriptions.manage']
          }
        ] as any
      }
    }

    if (endpoint.includes('/connect')) {
      const integrationType = endpoint.split('/').slice(-2)[0]
      return {
        data: {
          authorization_url: `/integrations/demo-oauth?integration=${integrationType}`,
          state: 'demo_state_12345'
        } as any
      }
    }

    if (endpoint.includes('/disconnect')) {
      return {
        data: { success: true } as any
      }
    }

    if (endpoint.includes('/status')) {
      return {
        data: {
          id: 'mock_id',
          integration_type: 'mock',
          is_connected: false,
          status: 'disconnected'
        } as any
      }
    }

    return { error: 'Mock endpoint not implemented' }
  }

  async getAvailableIntegrations(): Promise<{ data?: PartnerIntegration[]; error?: string }> {
    return this.request<PartnerIntegration[]>(`/admin/api/v1/partners/integrations/available?partner_id=${this.config.partnerId}&user_id=${this.config.userId}`)
  }

  async validateAccess(): Promise<{ data?: { valid: boolean; partner: any }; error?: string }> {
    return this.request<{ valid: boolean; partner: any }>(`/admin/api/v1/partners/validate?partner_id=${this.config.partnerId}&user_id=${this.config.userId}`)
  }

  async connectIntegration(integrationType: string): Promise<{ data?: OAuthResponse; error?: string }> {
    return this.request<OAuthResponse>(`/admin/api/v1/partners/integrations/${integrationType}/connect?partner_id=${this.config.partnerId}&user_id=${this.config.userId}`)
  }

  async disconnectIntegration(integrationType: string): Promise<{ data?: { success: boolean }; error?: string }> {
    return this.request<{ success: boolean }>(`/admin/api/v1/partners/integrations/${integrationType}/disconnect?partner_id=${this.config.partnerId}&user_id=${this.config.userId}`)
  }

  async getIntegrationStatus(integrationType: string): Promise<{ data?: PartnerIntegration; error?: string }> {
    return this.request<PartnerIntegration>(`/admin/api/v1/partners/integrations/${integrationType}/status?partner_id=${this.config.partnerId}&user_id=${this.config.userId}`)
  }
}