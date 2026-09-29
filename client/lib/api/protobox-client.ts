/**
 * ProtoboxClient - Unified API Client with Singleton Pattern
 * 
 * Features:
 * - Singleton instance across entire app
 * - Auto-injects workspace context and auth tokens
 * - Workspace readiness validation
 * - Middleware system for request/response interceptors
 * - Performance monitoring
 * - Type-safe API methods
 */

import { tokenManager } from '@/lib/auth/token-manager'
import { getApiBaseUrl } from './utils'
import { loggers } from '@/lib/logger'
import type { useAuthStore } from '@/lib/auth/stores/auth.store'

// Types
export interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  body?: any
  headers?: Record<string, string>
  timeout?: number
  skipWorkspaceValidation?: boolean // Skip workspace validation
}

export interface ApiResponse<T = any> {
  data?: T
  error?: string
  status: number
  timestamp?: string
}

export interface Middleware {
  onRequest?: (config: RequestConfig & { endpoint: string; url: string }) => RequestConfig & { endpoint: string; url: string }
  onResponse?: <T>(response: Response, data: T) => T
  onError?: (error: Error, config: RequestConfig & { endpoint: string }) => Error
}

/**
 * ProtoboxClient - Singleton API client
 */
export class ProtoboxClient {
  private static instance: ProtoboxClient
  private baseUrl: string
  private middlewares: Middleware[] = []
  private defaultHeaders: Record<string, string>

  private constructor() {
    this.baseUrl = getApiBaseUrl()
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
  }

  /**
   * Get singleton instance
   */
  static getInstance(): ProtoboxClient {
    if (!ProtoboxClient.instance) {
      ProtoboxClient.instance = new ProtoboxClient()
    }
    return ProtoboxClient.instance
  }

  /**
   * Add middleware for request/response interception
   */
  use(middleware: Middleware): void {
    this.middlewares.push(middleware)
  }

  /**
   * Remove all middlewares
   */
  clearMiddlewares(): void {
    this.middlewares = []
  }

  /**
   * Ensure workspace is ready before making workspace-scoped API calls
   * @throws Error if workspace is not ready
   */
  private ensureWorkspaceReady(): string {
    // Dynamically import to avoid circular dependency
    const { useAuthStore } = require('@/lib/auth/stores/auth.store') as {
      useAuthStore: typeof useAuthStore
    }
    
    const { currentWorkspace, workspaceLoading, error } = useAuthStore.getState()

    if (workspaceLoading) {
      throw new Error('Workspace still loading. Please wait before making API calls.')
    }

    if (error) {
      throw new Error(`Workspace error: ${error.message}`)
    }

    if (!currentWorkspace?._id) {
      throw new Error('No workspace selected. Please select a workspace first.')
    }

    return currentWorkspace._id
  }

  /**
   * Get auth headers from token manager
   */
  private getAuthHeaders(): Record<string, string> {
    return tokenManager.getAuthHeader()
  }

  /**
   * Core request method with middleware support
   */
  async request<T = any>(
    endpoint: string,
    config: RequestConfig = {}
  ): Promise<ApiResponse<T>> {
    const {
      method = 'GET',
      body,
      headers = {},
      timeout = 10000,
      skipWorkspaceValidation = false,
    } = config

    const startTime = performance.now()
    const cleanEndpoint = endpoint.replace(/\/+$/, '')
    const url = `${this.baseUrl}${cleanEndpoint}`

    // Build request config
    let requestConfig: RequestConfig & { endpoint: string; url: string } = {
      ...config,
      endpoint: cleanEndpoint,
      url,
      method,
      body,
      headers: { ...this.defaultHeaders, ...headers },
      timeout,
    }

    // Apply request middleware
    for (const middleware of this.middlewares) {
      if (middleware.onRequest) {
        requestConfig = middleware.onRequest(requestConfig)
      }
    }

    // Always add auth headers (getAuthHeaders returns {} if no token)
    const authHeaders = this.getAuthHeaders()
    requestConfig.headers = { ...requestConfig.headers, ...authHeaders }

    // Check token expiry only if Authorization header exists
    if (authHeaders.Authorization && tokenManager.isTokenExpired()) {
      loggers.api.info('Token expired before request', {
        endpoint: cleanEndpoint,
        method,
      })

      // Import auth store dynamically to avoid circular dependency
      const { useAuthStore } = await import('@/lib/auth/stores/auth.store')
      const authStore = useAuthStore.getState()

      if (authStore.isAuthenticated) {
        setTimeout(() => {
          authStore.signOut().catch((error) => {
            loggers.api.error('Proactive auto-logout failed', { error })
          })
        }, 100)

        return {
          error: 'Authentication expired',
          status: 401,
          timestamp: new Date().toISOString(),
        }
      }
    }

    // Create abort controller for timeout
    const abortController = new AbortController()
    const timeoutId = setTimeout(() => abortController.abort(), timeout)

    try {
      // For FormData, don't set Content-Type - browser sets it with boundary
      const fetchHeaders = body instanceof FormData
        ? Object.fromEntries(
            Object.entries(requestConfig.headers || {}).filter(
              ([key]) => key.toLowerCase() !== 'content-type'
            )
          )
        : requestConfig.headers

      const response = await fetch(requestConfig.url, {
        method: requestConfig.method,
        headers: fetchHeaders,
        body: body ? (body instanceof FormData ? body : JSON.stringify(body)) : undefined,
        signal: abortController.signal,
        credentials: 'include',
      })

      clearTimeout(timeoutId)

      const duration = performance.now() - startTime

      // Parse response
      let data: T
      const contentType = response.headers.get('content-type')
      if (contentType?.includes('application/json')) {
        data = await response.json()
      } else {
        data = (await response.text()) as T
      }

      // Apply response middleware
      for (const middleware of this.middlewares) {
        if (middleware.onResponse) {
          data = middleware.onResponse(response, data)
        }
      }

      // Log performance
      loggers.api.debug('API Request completed', {
        endpoint: cleanEndpoint,
        method,
        status: response.status,
        duration: `${duration.toFixed(2)}ms`,
      })

      if (!response.ok) {
        // Extract error message
        let errorMessage = `Request failed with status ${response.status}`
        if (data && typeof data === 'object' && 'error' in data) {
          errorMessage = String((data as any).error)
        } else if (data && typeof data === 'object' && 'detail' in data) {
          errorMessage = String((data as any).detail)
        } else if (data && typeof data === 'object' && 'message' in data) {
          errorMessage = String((data as any).message)
        }

        // Apply error middleware
        const error = new Error(errorMessage)
        let processedError = error
        for (const middleware of this.middlewares) {
          if (middleware.onError) {
            processedError = middleware.onError(processedError, {
              ...requestConfig,
              endpoint: cleanEndpoint,
            })
          }
        }

        // Handle 401 errors
        if (response.status === 401) {
          const { useAuthStore } = await import('@/lib/auth/stores/auth.store')
          const authStore = useAuthStore.getState()

          if (authStore.isAuthenticated) {
            setTimeout(() => {
              authStore.signOut().catch((err) => {
                loggers.api.error('Auto-logout failed', { error: err })
              })
            }, 100)
          }
        }

        return {
          error: processedError.message,
          status: response.status,
          timestamp: new Date().toISOString(),
        }
      }

      return {
        data,
        status: response.status,
        timestamp: new Date().toISOString(),
      }
    } catch (error) {
      clearTimeout(timeoutId)
      const duration = performance.now() - startTime

      // Apply error middleware
      let processedError = error instanceof Error ? error : new Error(String(error))
      for (const middleware of this.middlewares) {
        if (middleware.onError) {
          processedError = middleware.onError(processedError, {
            ...requestConfig,
            endpoint: cleanEndpoint,
          })
        }
      }

      loggers.api.error('API Request failed', {
        endpoint: cleanEndpoint,
        method,
        duration: `${duration.toFixed(2)}ms`,
        error: processedError.message,
      })

      return {
        error: processedError.message,
        status: 0,
        timestamp: new Date().toISOString(),
      }
    }
  }

  // Workspace-scoped methods (auto-inject workspaceId)

  /**
   * Get all workspaces for current user
   */
  async getWorkspaces(): Promise<ApiResponse<{ workspaces: any[]; user?: any }>> {
    return this.request('/workspaces')
  }

  /**
   * Get workspace by ID
   */
  async getWorkspace(workspaceId?: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}`)
  }

  /**
   * Create a new workspace
   */
  async createWorkspace(data: { name: string; slug?: string; description?: string; [key: string]: any }): Promise<ApiResponse<any>> {
    return this.request('/workspaces', {
      method: 'POST',
      body: data,
      skipWorkspaceValidation: true, // Creating workspace doesn't require existing workspace
    })
  }

  /**
   * Update workspace
   */
  async updateWorkspace(workspaceId: string, data: any): Promise<ApiResponse<any>> {
    return this.request(`/workspaces/${workspaceId}`, {
      method: 'PUT',
      body: data,
    })
  }

  /**
   * Delete workspace
   */
  async deleteWorkspace(workspaceId: string): Promise<ApiResponse<void>> {
    return this.request(`/workspaces/${workspaceId}`, {
      method: 'DELETE',
    })
  }

  // Actions methods (workspace-scoped)

  /**
   * List actions for workspace (auto-injects workspaceId)
   */
  async getActions(workspaceId?: string, params?: { type?: string; status?: string; tags?: string[] }): Promise<ApiResponse<any[]>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const queryParams = new URLSearchParams()
    if (params?.type) queryParams.append('type', params.type)
    if (params?.status) queryParams.append('status', params.status)
    if (params?.tags) params.tags.forEach(tag => queryParams.append('tags', tag))
    
    const queryString = queryParams.toString()
    const endpoint = `/workspaces/${wsId}/actions${queryString ? `?${queryString}` : ''}`
    return this.request(endpoint)
  }

  /**
   * Get single action
   */
  async getAction(workspaceId: string | undefined, actionId: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/${actionId}`)
  }

  /**
   * Create action
   */
  async createAction(workspaceId: string | undefined, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions`, {
      method: 'POST',
      body: data,
    })
  }

  /**
   * Update action
   */
  async updateAction(workspaceId: string | undefined, actionId: string, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/${actionId}`, {
      method: 'PUT',
      body: data,
    })
  }

  /**
   * Delete action
   */
  async deleteAction(workspaceId: string | undefined, actionId: string): Promise<ApiResponse<void>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/${actionId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Execute action
   */
  async executeAction(workspaceId: string | undefined, actionId: string, input?: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/${actionId}/test`, {
      method: 'POST',
      body: input || {},
    })
  }

  /**
   * Validate action
   */
  async validateAction(workspaceId: string | undefined, actionId: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/${actionId}/validate`, {
      method: 'POST',
    })
  }

  /**
   * Create CODE_RUN action
   */
  async createCodeRunAction(
    workspaceId: string | undefined,
    data: {
      name: string
      description: string
      language: 'python' | 'javascript'
      timeout?: number
      memory_limit_mb?: number
      allow_network?: boolean
      allow_file_ops?: boolean
      tags?: string
    }
  ): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const formData = new FormData()
    formData.append('name', data.name)
    formData.append('description', data.description)
    formData.append('type', 'CODE_RUN')
    formData.append('language', data.language)
    formData.append('timeout', (data.timeout || 30).toString())
    formData.append('memory_limit_mb', (data.memory_limit_mb || 128).toString())
    formData.append('allow_network', (data.allow_network || false).toString())
    formData.append('allow_file_ops', (data.allow_file_ops || false).toString())
    formData.append('tags', data.tags || '')
    
    return this.request(`/workspaces/${wsId}/actions`, {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
    })
  }

  /**
   * Get action types
   */
  async getActionTypes(workspaceId?: string): Promise<ApiResponse<any[]>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/types`)
  }

  /**
   * List action files
   */
  async getActionFiles(workspaceId: string | undefined, actionId: string): Promise<ApiResponse<any[]>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/${actionId}/files`)
  }

  /**
   * Get action file content (presigned URL)
   */
  async getActionFileContent(workspaceId: string | undefined, actionId: string, filename: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/${actionId}/files/${filename}`, {
      skipLoading: true,
    })
  }

  /**
   * Upload action file
   */
  async uploadActionFile(workspaceId: string | undefined, actionId: string, file: File): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const formData = new FormData()
    formData.append('file', file)
    return this.request(`/workspaces/${wsId}/actions/${actionId}/files`, {
      method: 'POST',
      body: formData,
      headers: {},
    })
  }

  /**
   * Update action file content
   */
  async updateActionFileContent(workspaceId: string | undefined, actionId: string, filename: string, content: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/${actionId}/files/${filename}/content`, {
      method: 'PUT',
      body: { content },
    })
  }

  /**
   * Delete action file
   */
  async deleteActionFile(workspaceId: string | undefined, actionId: string, filename: string): Promise<ApiResponse<void>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/${actionId}/files/${filename}`, {
      method: 'DELETE',
    })
  }

  /**
   * Deploy action
   */
  async deployAction(workspaceId: string | undefined, actionId: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/actions/${actionId}/deploy`, {
      method: 'POST',
    })
  }

  // Secrets methods (workspace-scoped)

  /**
   * List secrets for workspace
   */
  async getSecrets(workspaceId?: string, params?: { secret_type?: string; is_active?: boolean }): Promise<ApiResponse<any[]>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const queryParams = new URLSearchParams()
    if (params?.secret_type) queryParams.append('secret_type', params.secret_type)
    if (params?.is_active !== undefined) queryParams.append('is_active', String(params.is_active))
    
    const queryString = queryParams.toString()
    const endpoint = `/workspaces/${wsId}/secrets${queryString ? `?${queryString}` : ''}`
    return this.request(endpoint)
  }

  /**
   * Get single secret
   */
  async getSecret(workspaceId: string | undefined, secretId: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/secrets/${secretId}`)
  }

  /**
   * Create secret
   */
  async createSecret(workspaceId: string | undefined, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/secrets`, {
      method: 'POST',
      body: data,
    })
  }

  /**
   * Update secret
   */
  async updateSecret(workspaceId: string | undefined, secretId: string, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/secrets/${secretId}`, {
      method: 'PUT',
      body: data,
    })
  }

  /**
   * Delete secret
   */
  async deleteSecret(workspaceId: string | undefined, secretId: string): Promise<ApiResponse<void>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/secrets/${secretId}`, {
      method: 'DELETE',
    })
  }

  // Executions methods (workspace-scoped)

  /**
   * List executions for workspace
   */
  async getExecutions(
    workspaceId?: string,
    params?: { status?: string; action_id?: string; limit?: number; offset?: number; start_date?: string; end_date?: string }
  ): Promise<ApiResponse<any[]>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const queryParams = new URLSearchParams()
    if (params?.status) queryParams.append('status', params.status)
    if (params?.action_id) queryParams.append('action_id', params.action_id)
    if (params?.limit) queryParams.append('limit', String(params.limit))
    if (params?.offset) queryParams.append('offset', String(params.offset))
    if (params?.start_date) queryParams.append('start_date', params.start_date)
    if (params?.end_date) queryParams.append('end_date', params.end_date)
    
    const queryString = queryParams.toString()
    const endpoint = `/workspaces/${wsId}/executions${queryString ? `?${queryString}` : ''}`
    return this.request(endpoint)
  }

  /**
   * Get single execution
   */
  async getExecution(workspaceId: string | undefined, executionId: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/executions/${executionId}`)
  }

  /**
   * Cancel execution
   */
  async cancelExecution(workspaceId: string | undefined, executionId: string): Promise<ApiResponse<void>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/executions/${executionId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Retry execution
   */
  async retryExecution(workspaceId: string | undefined, executionId: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/executions/${executionId}/retry`, {
      method: 'POST',
    })
  }

  // User methods

  /**
   * Get current user profile
   */
  async getUserProfile(): Promise<ApiResponse<any>> {
    return this.request('/users/me')
  }

  /**
   * Update user preferences
   */
  async updateUserPreferences(preferences: any): Promise<ApiResponse<any>> {
    return this.request('/users/preferences', {
      method: 'PATCH',
      body: preferences,
    })
  }

  /**
   * Update user's last workspace
   */
  async updateLastWorkspace(workspaceId: string): Promise<ApiResponse<any>> {
    return this.request('/users/last-workspace', {
      method: 'PATCH',
      body: { workspace_id: workspaceId },
    })
  }

  // Assistant methods
  async getAssistants(workspaceId: string | undefined): Promise<ApiResponse<any[]>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/assistants`)
  }

  async getAssistant(workspaceId: string | undefined, assistantId: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/assistants/${assistantId}`)
  }

  async getOrCreateDefaultAssistant(workspaceId: string | undefined): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/assistants/default`)
  }

  async createAssistant(workspaceId: string | undefined, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/assistants`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateAssistant(workspaceId: string | undefined, assistantId: string, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/assistants/${assistantId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteAssistant(workspaceId: string | undefined, assistantId: string): Promise<ApiResponse<void>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/assistants/${assistantId}`, {
      method: 'DELETE',
    })
  }

  // Thread methods
  async createThread(workspaceId: string | undefined, assistantId: string, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/assistants/${assistantId}/threads`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async listThreads(workspaceId: string | undefined, assistantId: string): Promise<ApiResponse<any[]>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/assistants/${assistantId}/threads`)
  }

  // Message methods
  async getMessages(workspaceId: string | undefined, threadId: string, limit?: number): Promise<ApiResponse<any[]>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const params = limit ? `?limit=${limit}` : ''
    return this.request(`/workspaces/${wsId}/assistants/threads/${threadId}/messages${params}`)
  }

  async sendMessage(workspaceId: string | undefined, threadId: string, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/assistants/threads/${threadId}/messages`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // Integration methods
  async getAvailableIntegrations(): Promise<ApiResponse<any[]>> {
    return this.request('/integrations/available')
  }

  async getWorkspaceIntegrations(workspaceId: string | undefined): Promise<ApiResponse<any[]>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/integrations/`)
  }

  async connectIntegration(workspaceId: string | undefined, integrationType: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/integrations/${integrationType}/connect`, {
      method: 'POST',
    })
  }

  async resetIntegrationActions(workspaceId: string | undefined, integrationType: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/integrations/${integrationType}/reset`, {
      method: 'POST',
    })
  }

  async updateIntegrationSettings(workspaceId: string | undefined, integrationType: string, settings: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/integrations/${integrationType}/settings`, {
      method: 'PUT',
      body: settings,
    })
  }

  // Stats methods
  async getWorkspaceStats(workspaceId: string | undefined): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/stats`)
  }

  // Prompt methods
  async listPrompts(workspaceId: string | undefined, params?: {
    category?: string
    tags?: string[]
    is_active?: boolean
    is_system?: boolean
    skip?: number
    limit?: number
  }): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const searchParams = new URLSearchParams()
    if (params?.category) searchParams.append('category', params.category)
    if (params?.tags?.length) searchParams.append('tags', params.tags.join(','))
    if (params?.is_active !== undefined) searchParams.append('is_active', String(params.is_active))
    if (params?.is_system !== undefined) searchParams.append('is_system', String(params.is_system))
    if (params?.skip) searchParams.append('skip', String(params.skip))
    if (params?.limit) searchParams.append('limit', String(params.limit))
    const queryString = searchParams.toString()
    return this.request(`/workspaces/${wsId}/prompts${queryString ? `?${queryString}` : ''}`)
  }

  async getPrompt(workspaceId: string | undefined, promptId: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/prompts/${promptId}`)
  }

  async createPrompt(workspaceId: string | undefined, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/prompts`, {
      method: 'POST',
      body: data,
    })
  }

  async updatePrompt(workspaceId: string | undefined, promptId: string, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/prompts/${promptId}`, {
      method: 'PUT',
      body: data,
    })
  }

  async deletePrompt(workspaceId: string | undefined, promptId: string): Promise<ApiResponse<void>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/prompts/${promptId}`, {
      method: 'DELETE',
    })
  }

  async executePrompt(workspaceId: string | undefined, promptId: string, data: any): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/prompts/${promptId}/execute`, {
      method: 'POST',
      body: data,
    })
  }

  async getPromptVersions(workspaceId: string | undefined, promptId: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/prompts/${promptId}/versions`)
  }

  async getPromptVersion(workspaceId: string | undefined, promptId: string, version: number): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/prompts/${promptId}/versions/${version}`)
  }

  async restorePromptVersion(workspaceId: string | undefined, promptId: string, version: number): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/prompts/${promptId}/restore/${version}`, {
      method: 'POST',
    })
  }

  async getPromptUsageStats(workspaceId: string | undefined, days: number = 30): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/prompts/stats/usage?days=${days}`)
  }

  // Analytics methods
  async getDashboardStats(workspaceId: string | undefined, timeRange: string = '7d'): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/analytics/dashboard-stats?time_range=${timeRange}`)
  }

  async getExecutionMetrics(workspaceId: string | undefined, timeRange: string = '7d'): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/analytics/execution-metrics?time_range=${timeRange}`)
  }

  async getRecentActivity(workspaceId: string | undefined, limit: number = 10): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/analytics/recent-activity?limit=${limit}`)
  }

  async getTopActions(workspaceId: string | undefined, timeRange: string = '7d', limit: number = 10): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/analytics/top-actions?time_range=${timeRange}&limit=${limit}`)
  }

  // Knowledge Base methods (workspace-scoped)

  /**
   * List knowledge documents in a workspace
   */
  async listKnowledgeDocuments(
    workspaceId?: string,
    params?: { skip?: number; limit?: number; category?: string; status?: string }
  ): Promise<ApiResponse<any[]>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const queryParams = new URLSearchParams()
    if (params?.skip) queryParams.append('skip', String(params.skip))
    if (params?.limit) queryParams.append('limit', String(params.limit))
    if (params?.category) queryParams.append('category', params.category)
    if (params?.status) queryParams.append('status', params.status)

    const queryString = queryParams.toString()
    const endpoint = `/workspaces/${wsId}/knowledge${queryString ? `?${queryString}` : ''}`
    return this.request(endpoint)
  }

  /**
   * Get a knowledge document with its chunks
   */
  async getKnowledgeDocument(
    workspaceId: string | undefined,
    documentId: string,
    params?: { skip?: number; limit?: number }
  ): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const queryParams = new URLSearchParams()
    if (params?.skip) queryParams.append('skip', String(params.skip))
    if (params?.limit) queryParams.append('limit', String(params.limit))

    const queryString = queryParams.toString()
    const endpoint = `/workspaces/${wsId}/knowledge/${documentId}${queryString ? `?${queryString}` : ''}`
    return this.request(endpoint)
  }

  /**
   * Upload a knowledge source (file, URL, or text)
   */
  async uploadKnowledgeSource(
    workspaceId: string | undefined,
    data: {
      file?: File
      title?: string
      description?: string
      category?: string
      tags?: string[]
      source_type: 'file' | 'url' | 'text'
      url?: string
      content?: string
      chunking_strategy?: string
      chunk_size?: number
      chunk_overlap?: number
    }
  ): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const formData = new FormData()

    if (data.file) formData.append('file', data.file)
    if (data.title) formData.append('title', data.title)
    if (data.description) formData.append('description', data.description)
    formData.append('category', data.category || 'general')
    formData.append('tags', data.tags?.join(',') || '')
    formData.append('source_type', data.source_type)
    if (data.url) formData.append('url', data.url)
    if (data.content) formData.append('content', data.content)
    formData.append('chunking_strategy', data.chunking_strategy || 'smart')
    if (data.chunk_size) formData.append('chunk_size', String(data.chunk_size))
    if (data.chunk_overlap) formData.append('chunk_overlap', String(data.chunk_overlap))

    return this.request(`/workspaces/${wsId}/knowledge/upload`, {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
      timeout: 60000, // Longer timeout for file uploads
    })
  }

  /**
   * Delete a knowledge document
   */
  async deleteKnowledgeDocument(workspaceId: string | undefined, documentId: string): Promise<ApiResponse<void>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/knowledge/${documentId}`, {
      method: 'DELETE',
    })
  }

  /**
   * Replace a knowledge document's source
   */
  async replaceKnowledgeDocument(
    workspaceId: string | undefined,
    documentId: string,
    data: {
      file?: File
      url?: string
      content?: string
      chunking_strategy?: string
      chunk_size?: number
      chunk_overlap?: number
    }
  ): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    const formData = new FormData()

    if (data.file) formData.append('file', data.file)
    if (data.url) formData.append('url', data.url)
    if (data.content) formData.append('content', data.content)
    if (data.chunking_strategy) formData.append('chunking_strategy', data.chunking_strategy)
    if (data.chunk_size) formData.append('chunk_size', String(data.chunk_size))
    if (data.chunk_overlap) formData.append('chunk_overlap', String(data.chunk_overlap))

    return this.request(`/workspaces/${wsId}/knowledge/${documentId}/upload`, {
      method: 'PUT',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
      timeout: 60000, // Longer timeout for file uploads
    })
  }

  /**
   * Query the knowledge base using semantic/hybrid search
   */
  async queryKnowledgeBase(
    workspaceId: string | undefined,
    query: {
      query: string
      top_k?: number
      min_score?: number
      search_type?: 'semantic' | 'keyword' | 'hybrid'
      rerank?: boolean
      document_ids?: string[]
      categories?: string[]
      tags?: string[]
    }
  ): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/knowledge/query`, {
      method: 'POST',
      body: query,
    })
  }

  /**
   * Get the status of a document processing task
   */
  async getKnowledgeProcessingStatus(workspaceId: string | undefined, taskId: string): Promise<ApiResponse<any>> {
    const wsId = workspaceId || this.ensureWorkspaceReady()
    return this.request(`/workspaces/${wsId}/knowledge/tasks/${taskId}`)
  }

  /**
   * Alias for getKnowledgeProcessingStatus (backward compatibility)
   */
  async getKnowledgeUploadStatus(workspaceId: string | undefined, taskId: string): Promise<ApiResponse<any>> {
    return this.getKnowledgeProcessingStatus(workspaceId, taskId)
  }

  /**
   * Upload a file to the knowledge base (convenience method)
   */
  async uploadKnowledgeFile(
    workspaceId: string | undefined,
    file: File,
    options?: { chunking_strategy?: string; category?: string; tags?: string[] }
  ): Promise<ApiResponse<any>> {
    return this.uploadKnowledgeSource(workspaceId, {
      file,
      title: file.name,
      source_type: 'file',
      category: options?.category,
      tags: options?.tags,
      chunking_strategy: options?.chunking_strategy,
    })
  }

  /**
   * Upload a URL to the knowledge base (convenience method)
   */
  async uploadKnowledgeUrl(
    workspaceId: string | undefined,
    url: string,
    options?: { title?: string; chunking_strategy?: string; category?: string; tags?: string[]; crawl_depth?: number }
  ): Promise<ApiResponse<any>> {
    return this.uploadKnowledgeSource(workspaceId, {
      url,
      title: options?.title || `Web content from ${url}`,
      source_type: 'url',
      category: options?.category,
      tags: options?.tags,
      chunking_strategy: options?.chunking_strategy,
    })
  }

  /**
   * Upload text content to the knowledge base (convenience method)
   */
  async uploadKnowledgeText(
    workspaceId: string | undefined,
    title: string,
    content: string,
    options?: { chunking_strategy?: string; category?: string; tags?: string[] }
  ): Promise<ApiResponse<any>> {
    return this.uploadKnowledgeSource(workspaceId, {
      title,
      content,
      source_type: 'text',
      category: options?.category,
      tags: options?.tags,
      chunking_strategy: options?.chunking_strategy,
    })
  }

  /**
   * Query the knowledge base (convenience alias)
   */
  async queryKnowledge(
    workspaceId: string | undefined,
    queryText: string,
    options?: {
      top_k?: number
      min_score?: number
      search_type?: 'semantic' | 'keyword' | 'hybrid'
      rerank?: boolean
      document_ids?: string[]
      categories?: string[]
      tags?: string[]
    }
  ): Promise<ApiResponse<any>> {
    return this.queryKnowledgeBase(workspaceId, {
      query: queryText,
      ...options,
    })
  }

  /**
   * Replace a knowledge document with a new file (convenience method)
   */
  async replaceKnowledgeFile(
    workspaceId: string | undefined,
    documentId: string,
    file: File,
    options?: { chunking_strategy?: string }
  ): Promise<ApiResponse<any>> {
    return this.replaceKnowledgeDocument(workspaceId, documentId, {
      file,
      chunking_strategy: options?.chunking_strategy,
    })
  }

  /**
   * Replace a knowledge document with a new URL (convenience method)
   */
  async replaceKnowledgeUrl(
    workspaceId: string | undefined,
    documentId: string,
    url: string,
    options?: { chunking_strategy?: string }
  ): Promise<ApiResponse<any>> {
    return this.replaceKnowledgeDocument(workspaceId, documentId, {
      url,
      chunking_strategy: options?.chunking_strategy,
    })
  }

  /**
   * Replace a knowledge document with new text content (convenience method)
   */
  async replaceKnowledgeText(
    workspaceId: string | undefined,
    documentId: string,
    content: string,
    options?: { chunking_strategy?: string }
  ): Promise<ApiResponse<any>> {
    return this.replaceKnowledgeDocument(workspaceId, documentId, {
      content,
      chunking_strategy: options?.chunking_strategy,
    })
  }

  // Auth methods - no skipAuth needed (getAuthHeaders returns {} when no token)
  async exchangeToken(firebaseToken: string): Promise<ApiResponse<any>> {
    return this.request('/auth/exchange', {
      method: 'POST',
      body: { firebase_token: firebaseToken },
    })
  }

  async logout(): Promise<ApiResponse<void>> {
    return this.request('/auth/revoke', {
      method: 'POST',
    })
  }

  async refreshToken(): Promise<ApiResponse<any>> {
    return this.request('/auth/refresh', {
      method: 'POST',
    })
  }

  async validateToken(): Promise<ApiResponse<any>> {
    return this.request('/auth/validate')
  }
}

// Export singleton instance
export const protoboxClient = ProtoboxClient.getInstance()

// Initialize default middlewares on first import (client-side only)
// This ensures middlewares are set up before any API calls
if (typeof window !== 'undefined') {
  // Use IIFE to initialize immediately but avoid blocking
  ;(async () => {
    try {
      // Dynamic import to avoid circular dependencies
      const { initializeMiddlewares } = await import('./middleware')
      initializeMiddlewares()
    } catch (error) {
      // Silently fail if middleware initialization fails (e.g., in SSR)
      if (process.env.NODE_ENV === 'development') {
        console.debug('Middleware initialization failed', error)
      }
    }
  })()
}

