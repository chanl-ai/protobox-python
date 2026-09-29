import { protoboxClient } from '@/lib/api/protobox-client'

export interface MCPOAuthClient {
  client_id: string
  client_name: string
  redirect_uris: string[]
  allowed_scopes: string[]
  description?: string
  logo_uri?: string
  client_uri?: string
  created_at: string
  last_used_at?: string
  status: 'active' | 'revoked'
}

export interface CreateOAuthClientRequest {
  client_name: string
  redirect_uris: string[]
  description?: string
  logo_uri?: string
  client_uri?: string
  scopes?: string[]
  token_endpoint_auth_method?: string  // For confidential clients
  client_type?: 'public' | 'confidential'  // Client type
}

export interface CreateOAuthClientResponse {
  client_id: string
  client_secret: string  // Only shown once!
  client_name: string
  redirect_uris: string[]
  allowed_scopes: string[]
  created_at: string
  message: string
}

export interface OAuthServerMetadata {
  issuer: string
  authorization_endpoint: string
  token_endpoint: string
  introspection_endpoint: string
  revocation_endpoint: string
  response_types_supported: string[]
  grant_types_supported: string[]
  code_challenge_methods_supported: string[]
  scopes_supported: string[]
  token_endpoint_auth_methods_supported: string[]
  service_documentation: string
}

class MCPOAuthAPI {
  async createClient(
    workspaceId: string,
    data: CreateOAuthClientRequest
  ): Promise<CreateOAuthClientResponse> {
    const response = await protoboxClient.createMCPOAuthClient(workspaceId, {
      ...data,
      scopes: data.scopes || ['mcp:read', 'mcp:execute']
    })
    
    if (response.error) {
      throw new Error(response.error)
    }
    
    return response.data!
  }

  async listClients(workspaceId: string): Promise<MCPOAuthClient[]> {
    const response = await protoboxClient.listMCPOAuthClients(workspaceId)
    
    if (response.error) {
      throw new Error(response.error)
    }
    
    return response.data || []
  }

  async revokeClient(
    workspaceId: string,
    clientId: string
  ): Promise<{ message: string }> {
    const response = await protoboxClient.deleteMCPOAuthClient(workspaceId, clientId)
    
    if (response.error) {
      throw new Error(response.error)
    }
    
    return { message: 'Client revoked successfully' }
  }

  async getServerMetadata(workspaceId: string): Promise<OAuthServerMetadata> {
    const response = await protoboxClient.getMCPOAuthServerMetadata(workspaceId)
    
    if (response.error) {
      throw new Error(response.error)
    }
    
    return response.data!
  }
}

export const mcpOAuthApi = new MCPOAuthAPI()