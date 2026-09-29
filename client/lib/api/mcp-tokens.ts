import { protoboxClient } from '@/lib/api/protobox-client'
import { withCache, cacheKeys, cacheTTL, apiCache } from '@/lib/api/cache'

export interface MCPToken {
  token_id: string
  name: string
  description?: string
  workspace_id: string
  scopes: string[]
  expires_at?: string
  created_at: string
  last_used_at?: string
  usage_count: number
  status: 'active' | 'revoked' | 'expired'
}

export interface CreateMCPTokenRequest {
  name: string
  description?: string
  expires_in_days?: number
  scopes?: string[]
}

export interface CreateMCPTokenResponse {
  token: string  // Plain token - only shown once!
  token_id: string
  name: string
  workspace_id: string
  mcp_url: string  // Full URL to use with MCP clients
  expires_at?: string
  message: string
}

class MCPTokensAPI {
  async create(workspaceId: string, data: CreateMCPTokenRequest): Promise<CreateMCPTokenResponse> {
    const response = await protoboxClient.createMCPToken(workspaceId, data)
    
    if (response.error) {
      throw new Error(response.error)
    }

    // Clear cache after creating new token
    apiCache.delete(cacheKeys.mcpTokens(workspaceId))
    
    return response.data!
  }

  async list(workspaceId: string, includeRevoked = false): Promise<MCPToken[]> {
    return withCache(
      `${cacheKeys.mcpTokens(workspaceId)}:${includeRevoked}`,
      async () => {
        const params = includeRevoked ? { include_revoked: 'true' } : undefined
        
        const response = await protoboxClient.listMCPTokens(workspaceId)
        
        if (response.error) {
          throw new Error(response.error)
        }
        
        return response.data || []
      },
      cacheTTL.tokens
    )
  }

  async revoke(workspaceId: string, tokenId: string): Promise<{ message: string }> {
    const response = await protoboxClient.deleteMCPToken(workspaceId, tokenId)
    
    if (response.error) {
      throw new Error(response.error)
    }

    // Clear cache after revoking token
    apiCache.delete(cacheKeys.mcpTokens(workspaceId))
    
    return { message: 'Token revoked successfully' }
  }
}

export const mcpTokensApi = new MCPTokensAPI()