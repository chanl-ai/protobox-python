/**
 * Type definitions for API entities
 * 
 * These types were extracted from client.ts after migrating to protoboxClient.
 * Import these types instead of importing from the deprecated client.ts
 */

export interface Integration {
  id: string
  name: string
  type: string
  status: 'connected' | 'not_connected'
  workspace_id: string
  oauth_data?: any
  api_key_secret_id?: string
  created_at: string
  updated_at: string
}

export interface IntegrationUIConfig {
  id: string
  name: string
  description: string
  icon?: string
  category: string
  status?: 'connected' | 'not_connected'
  capabilities?: string[]
}

export interface WorkspaceListResponse {
  workspaces: any[]
  user?: {
    last_workspace_id?: string
  }
}

export interface Action {
  id: string
  workspace_id: string
  name: string
  description?: string
  type: string
  version?: string
  tags?: string[]
  config_schema?: any
  default_config?: any
  secret_refs?: string[]
  status?: string
  is_builtin?: boolean
  created_by: string
  created_at: string
  updated_at: string
}

export interface Secret {
  id: string
  name: string
  description?: string
  secret_type: string
  secret_value?: string // Only present during creation/updates
  tags?: string[]
  is_active: boolean
  created_at: string
  updated_at: string
  expires_at?: string
  usage_count: number
  max_usage_count?: number
}

export interface Execution {
  id: string
  action_id: string
  action_name?: string
  workspace_id: string
  user_id: string
  user_name?: string
  status: "pending" | "running" | "completed" | "failed" | "cancelled"
  started_at: string
  completed_at?: string
  execution_time_ms?: number
  error_message?: string
  output_data?: any
  retry_count: number
  can_retry: boolean
}

export interface WorkspaceStats {
  actions_count: number
  mcp_tokens_count: number
  oauth_clients_count: number
  integrations_count: number
  knowledge_docs_count: number
}

