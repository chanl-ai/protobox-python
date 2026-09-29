/**
 * ProtoBox Partner SDK
 * This is what partners would use to authenticate and communicate with ProtoBox
 */

import crypto from 'crypto'

export class ProtoBoxPartnerClient {
  private partnerId: string
  private secretKey: string
  private apiUrl: string

  constructor(config: {
    partnerId: string
    secretKey: string
    apiUrl?: string
  }) {
    this.partnerId = config.partnerId
    this.secretKey = config.secretKey
    this.apiUrl = config.apiUrl || 'http://localhost:3010/api/partner'
  }

  /**
   * Generate signed request payload
   */
  private generateSignedPayload(
    partnerUserId: string,
    endpoint: string,
    additionalData?: any
  ) {
    const payload = {
      partner_id: this.partnerId,
      partner_user_id: partnerUserId,
      timestamp: Date.now(),
      endpoint,
      ...additionalData
    }

    const signature = crypto
      .createHmac('sha256', this.secretKey)
      .update(JSON.stringify(payload))
      .digest('hex')

    return { payload, signature }
  }

  /**
   * Fetch integrations for a partner user
   */
  async getIntegrations(partnerUserId: string) {
    const { payload, signature } = this.generateSignedPayload(
      partnerUserId,
      'integrations'
    )

    const response = await fetch(`${this.apiUrl}/integrations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Partner-Signature': signature
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to fetch integrations')
    }

    return response.json()
  }

  /**
   * Get actions for a partner user
   */
  async getActions(partnerUserId: string) {
    const { payload, signature } = this.generateSignedPayload(
      partnerUserId,
      'actions'
    )

    const response = await fetch(`${this.apiUrl}/actions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Partner-Signature': signature
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to fetch actions')
    }

    return response.json()
  }

  /**
   * Generate embed URL with pre-authenticated token
   */
  generateEmbedUrl(partnerUserId: string, options: {
    type: 'integrations' | 'actions'
    baseUrl?: string
  }) {
    const { payload, signature } = this.generateSignedPayload(
      partnerUserId,
      options.type
    )

    // Encode the authentication data
    const authData = Buffer.from(JSON.stringify({
      payload,
      signature
    })).toString('base64')

    const baseUrl = options.baseUrl || 'http://localhost:3010'
    return `${baseUrl}/embed/partner/${options.type}?auth=${authData}`
  }
}

// Example usage for partners:
/*
const protobox = new ProtoBoxPartnerClient({
  partnerId: 'demo_partner',
  secretKey: 'demo_secret_key_123',
  apiUrl: 'http://localhost:3001/api/partner' // For testing
})

// Get integrations for a user
const integrations = await protobox.getIntegrations('demo_user_1')

// Generate embed URL
const embedUrl = protobox.generateEmbedUrl('demo_user_1', {
  type: 'integrations',
  baseUrl: 'http://localhost:3001'
})
*/