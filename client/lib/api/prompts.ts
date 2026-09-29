import { protoboxClient } from './protobox-client'

export interface PromptMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface PromptArgument {
  name: string
  description: string
  type: 'string' | 'number' | 'boolean' | 'array' | 'object'
  required: boolean
  default?: any
}

export interface Prompt {
  id: string
  workspace_id: string
  name: string
  description: string
  messages: PromptMessage[]
  arguments: PromptArgument[]
  category: string
  tags: string[]
  is_active: boolean
  is_system: boolean
  usage_count: number
  last_used_at?: string
  version: number
  created_at: string
  updated_at: string
  created_by: string
  updated_by: string
}

export interface PromptCreateRequest {
  name: string
  description: string
  messages: PromptMessage[]
  arguments?: PromptArgument[]
  category?: string
  tags?: string[]
  is_active?: boolean
}

export interface PromptUpdateRequest {
  name?: string
  description?: string
  messages?: PromptMessage[]
  arguments?: PromptArgument[]
  category?: string
  tags?: string[]
  is_active?: boolean
}

export interface PromptListResponse {
  prompts: Prompt[]
  total: number
  category_filter?: string
  tags_filter?: string[]
}

export interface PromptExecuteRequest {
  arguments: Record<string, any>
}

export interface PromptExecuteResponse {
  rendered_messages: Array<{ role: string; content: string }>
  argument_validation: {
    valid: boolean
    missing_required: string[]
    invalid_types: string[]
    warnings: string[]
  }
  execution_time_ms: number
}

export interface PromptVersion {
  id: string
  prompt_id: string
  version: number
  name: string
  description: string
  messages: PromptMessage[]
  arguments: PromptArgument[]
  category: string
  tags: string[]
  change_summary: string
  created_at: string
  created_by: string
}

class PromptsAPI {
  private baseUrl = '/workspaces'

  async listPrompts(
    workspaceId: string,
    params?: {
      category?: string
      tags?: string[]
      is_active?: boolean
      is_system?: boolean
      skip?: number
      limit?: number
    }
  ): Promise<PromptListResponse> {
    const searchParams = new URLSearchParams()
    
    if (params?.category) searchParams.append('category', params.category)
    if (params?.tags?.length) searchParams.append('tags', params.tags.join(','))
    if (params?.is_active !== undefined) searchParams.append('is_active', String(params.is_active))
    if (params?.is_system !== undefined) searchParams.append('is_system', String(params.is_system))
    if (params?.skip) searchParams.append('skip', String(params.skip))
    if (params?.limit) searchParams.append('limit', String(params.limit))

    const queryString = searchParams.toString()
    const url = `${this.baseUrl}/${workspaceId}/prompts${queryString ? `?${queryString}` : ''}`
    
    const response = await protoboxClient.listPrompts(workspaceId, params)
    return response.data || { prompts: [], total: 0 }
  }

  async getPrompt(workspaceId: string, promptId: string): Promise<Prompt> {
    const response = await protoboxClient.getPrompt(workspaceId, promptId)
    return response.data?.prompt || response.data
  }

  async createPrompt(workspaceId: string, data: PromptCreateRequest): Promise<Prompt> {
    const response = await protoboxClient.createPrompt(workspaceId, data)
    return response.data
  }

  async updatePrompt(workspaceId: string, promptId: string, data: PromptUpdateRequest): Promise<Prompt> {
    const response = await protoboxClient.updatePrompt(workspaceId, promptId, data)
    return response.data
  }

  async deletePrompt(workspaceId: string, promptId: string): Promise<void> {
    await protoboxClient.deletePrompt(workspaceId, promptId)
  }

  async executePrompt(
    workspaceId: string, 
    promptId: string, 
    data: PromptExecuteRequest
  ): Promise<PromptExecuteResponse> {
    const response = await protoboxClient.executePrompt(workspaceId, promptId, data)
    return response.data
  }

  // Note: These methods would need to be implemented in the backend
  // For now, they return mock data or throw errors
  
  async duplicatePrompt(workspaceId: string, promptId: string, data: PromptCreateRequest): Promise<Prompt> {
    // TODO: Implement in backend
    throw new Error("Duplicate prompt not yet implemented in backend")
  }

  async getPromptVersions(workspaceId: string, promptId: string): Promise<{
    versions: PromptVersion[]
    total: number
    current_version: number
  }> {
    const response = await protoboxClient.getPromptVersions(workspaceId, promptId)
    return response.data
  }

  async getPromptVersion(workspaceId: string, promptId: string, version: number): Promise<PromptVersion> {
    const response = await protoboxClient.getPromptVersion(workspaceId, promptId, version)
    return response.data
  }

  async restorePromptVersion(workspaceId: string, promptId: string, version: number): Promise<Prompt> {
    const response = await protoboxClient.restorePromptVersion(workspaceId, promptId, version)
    return response.data
  }

  async exportPrompt(workspaceId: string, promptId: string, format: 'json' | 'yaml' | 'markdown' | 'text'): Promise<string> {
    // TODO: Implement in backend
    throw new Error("Export prompt not yet implemented in backend")
  }

  async getPromptUsageStats(workspaceId: string, days: number = 30): Promise<any> {
    const response = await protoboxClient.getPromptUsageStats(workspaceId, days)
    return response.data
  }
}

export const promptsApi = new PromptsAPI()

// Export individual methods for convenience
export const getPrompt = promptsApi.getPrompt.bind(promptsApi)
export const deletePrompt = promptsApi.deletePrompt.bind(promptsApi)
