import { AuthProvider } from '../auth/auth-context'

interface EmbedApiConfig {
  provider: AuthProvider
  token: string
  workspaceId: string
  partnerSignature?: string
}

class EmbedApiClient {
  private config: EmbedApiConfig | null = null

  configure(config: EmbedApiConfig) {
    this.config = config
  }

  private async generateSignature(payload: any, secretKey: string): Promise<string> {
    const encoder = new TextEncoder()
    const keyData = encoder.encode(secretKey)
    const messageData = encoder.encode(JSON.stringify(payload))
    
    const cryptoKey = await crypto.subtle.importKey(
      'raw',
      keyData,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    )
    
    const signature = await crypto.subtle.sign(
      'HMAC',
      cryptoKey,
      messageData
    )
    
    return Array.from(new Uint8Array(signature))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('')
  }

  private async makeRequest(endpoint: string, options: RequestInit = {}) {
    if (!this.config) {
      throw new Error('EmbedApiClient not configured')
    }

    const { provider, token, workspaceId, partnerSignature } = this.config

    if (provider === 'firebase') {
      // Use backend API routes with Firebase auth
      const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8090'
      const response = await fetch(`${BACKEND_URL}/admin/api/v1/workspaces/${workspaceId}${endpoint}`, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          ...options.headers
        }
      })
      return response
    } else if (provider === 'partner') {
      // For partner auth, we need to create a new signed request for each API call
      
      // Clean endpoint for partner API
      const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint

      // Create payload with current timestamp
      const payload: any = {
        partner_id: 'demo_partner',
        partner_user_id: 'demo_user_1', 
        timestamp: Date.now()
      }
      
      // Only add data for non-GET requests with body
      if (options.method !== 'GET' && options.body) {
        payload.data = JSON.parse(options.body as string)
      }

      // Debug logging removed

      // Generate signature using the secret key (demo only - never do this in production!)
      const signature = await this.generateSignature(payload, token)


      const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8090'
      const url = `${BACKEND_URL}/admin/api/v1/partner/${cleanEndpoint}`

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Partner-Signature': signature,
          ...options.headers
        },
        body: JSON.stringify(payload)
      })

      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(errorText)
      }

      return response
    }

    throw new Error(`Unknown auth provider: ${provider}`)
  }

  async get(endpoint: string) {
    const response = await this.makeRequest(endpoint, { method: 'GET' })
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    return response.json()
  }

  async post(endpoint: string, data: any) {
    const response = await this.makeRequest(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    return response.json()
  }

  async put(endpoint: string, data: any) {
    const response = await this.makeRequest(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data)
    })
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    return response.json()
  }

  async delete(endpoint: string) {
    const response = await this.makeRequest(endpoint, {
      method: 'DELETE'
    })
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    return response.json()
  }
}

export const embedApiClient = new EmbedApiClient()