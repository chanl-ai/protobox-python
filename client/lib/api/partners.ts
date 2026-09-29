/**
 * Partner API client
 */

import { protoboxClient } from './protobox-client'

export interface PartnerConversionRequest {
  business_name: string
  contact_email: string
  industry?: string
  description?: string
  website?: string
}

export interface Partner {
  partner_id: string
  user_id?: string
  business_name: string
  contact_email?: string
  industry?: string
  secret_key: string
  allowed_domains: string[]
  allowed_endpoints: string[]
  rate_limit: number
  webhook_url?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PartnerStats {
  total_customers: number
  active_integrations: number
  monthly_requests: number
  revenue: number
  last_30_days_growth?: {
    customers: number
    requests: number
    revenue: number
  }
}

export interface PartnerCustomer {
  tenant_id: string
  workspace_id: string
  customer_name?: string
  integrations_count: number
  last_active?: string
  status: string
  total_requests: number
}

export interface PartnerStatus {
  is_partner: boolean
  partner_id?: string
  business_name?: string
}

class PartnerApi {
  /**
   * Convert current user to a partner
   */
  async convertToPartner(request: PartnerConversionRequest): Promise<Partner> {
    const response = await protoboxClient.request<Partner>('/partners/convert', {
      method: 'POST',
      body: request,
    })
    
    // Check if response has error
    if (response.error) {
      throw new Error(response.error)
    }
    
    // Check if response has data
    if (!response.data) {
      throw new Error('No data received from server')
    }
    
    return response.data
  }

  /**
   * Get current user's partner account
   */
  async getMyPartnerAccount(): Promise<Partner> {
    const response = await protoboxClient.request<Partner>('/partners/me')
    
    // Check if response has error
    if (response.error) {
      throw new Error(response.error)
    }
    
    // Check if response has data
    if (!response.data) {
      throw new Error('No data received from server')
    }
    
    return response.data
  }

  /**
   * Get partner statistics
   */
  async getPartnerStats(partnerId: string): Promise<PartnerStats> {
    const response = await protoboxClient.request<PartnerStats>(`/partners/${partnerId}/stats`)
    
    // Check if response has error
    if (response.error) {
      throw new Error(response.error)
    }
    
    // Check if response has data
    if (!response.data) {
      throw new Error('No data received from server')
    }
    
    return response.data
  }

  /**
   * Get partner customers (workspaces managed by this partner)
   */
  async getPartnerCustomers(partnerId: string): Promise<PartnerCustomer[]> {
    const response = await protoboxClient.request<PartnerCustomer[]>(`/partners/${partnerId}/customers`)
    
    // Check if response has error
    if (response.error) {
      throw new Error(response.error)
    }
    
    // Check if response has data
    if (!response.data) {
      throw new Error('No data received from server')
    }
    
    return response.data
  }

  /**
   * Check if current user is a partner
   */
  async checkPartnerStatus(): Promise<PartnerStatus> {
    const response = await protoboxClient.request<PartnerStatus>('/partners/status')
    
    // Check if response has error
    if (response.error) {
      throw new Error(response.error)
    }
    
    // Check if response has data
    if (!response.data) {
      throw new Error('No data received from server')
    }
    
    return response.data
  }
}

export const partnerApi = new PartnerApi()