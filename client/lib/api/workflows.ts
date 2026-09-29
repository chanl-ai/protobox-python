import { protoboxClient } from './protobox-client'

export interface Workflow {
  id: string
  name: string
  description?: string
  version: string
  tags: string[]
  status: 'active' | 'inactive' | 'error' | 'scheduled'
  config_schema?: any
  created_at: string
  updated_at: string
  created_by?: string
  workspace_id: string
}

export interface CreateWorkflowData {
  name: string
  description?: string
  version: string
  tags: string[]
  config_schema?: any
}

export interface UpdateWorkflowData {
  name?: string
  description?: string
  version?: string
  tags?: string[]
  config_schema?: any
}

export const workflowsApi = {
  // List all workflows for a workspace
  list: async (workspaceId: string): Promise<{ data: Workflow[]; error?: string }> => {
    try {
      const response = await protoboxClient.request(`/workspaces/${workspaceId}/workflows`)
      return { data: response.data || [] }
    } catch (error: any) {
      return { data: [], error: error.message || 'Failed to fetch workflows' }
    }
  },

  // Get a specific workflow
  get: async (workspaceId: string, workflowId: string): Promise<{ data: Workflow | null; error?: string }> => {
    try {
      const response = await protoboxClient.request(`/workspaces/${workspaceId}/workflows/${workflowId}`)
      return { data: response.data }
    } catch (error: any) {
      return { data: null, error: error.message || 'Failed to fetch workflow' }
    }
  },

  // Create a new workflow
  create: async (workspaceId: string, data: CreateWorkflowData): Promise<{ data: Workflow | null; error?: string }> => {
    try {
      const response = await protoboxClient.request(`/workspaces/${workspaceId}/workflows`, { method: 'POST', body: data })
      return { data: response.data }
    } catch (error: any) {
      return { data: null, error: error.message || 'Failed to create workflow' }
    }
  },

  // Update an existing workflow
  update: async (workspaceId: string, workflowId: string, data: UpdateWorkflowData): Promise<{ data: Workflow | null; error?: string }> => {
    try {
      const response = await protoboxClient.request(`/workspaces/${workspaceId}/workflows/${workflowId}`, { method: 'PUT', body: data })
      return { data: response.data }
    } catch (error: any) {
      return { data: null, error: error.message || 'Failed to update workflow' }
    }
  },

  // Delete a workflow
  delete: async (workspaceId: string, workflowId: string): Promise<{ status: number; error?: string }> => {
    try {
      const response = await protoboxClient.request(`/workspaces/${workspaceId}/workflows/${workflowId}`, { method: 'DELETE' })
      return { status: response.status }
    } catch (error: any) {
      return { status: 500, error: error.message || 'Failed to delete workflow' }
    }
  },

  // Execute a workflow
  execute: async (workspaceId: string, workflowId: string, input?: any): Promise<{ data: any; error?: string }> => {
    try {
      const response = await protoboxClient.request(`/workspaces/${workspaceId}/workflows/${workflowId}/execute`, { method: 'POST', body: { input } })
      return { data: response.data }
    } catch (error: any) {
      return { data: null, error: error.message || 'Failed to execute workflow' }
    }
  },

  // Duplicate a workflow
  duplicate: async (workspaceId: string, workflowId: string): Promise<{ data: Workflow | null; error?: string }> => {
    try {
      const response = await protoboxClient.request(`/workspaces/${workspaceId}/workflows/${workflowId}/duplicate`, { method: 'POST' })
      return { data: response.data }
    } catch (error: any) {
      return { data: null, error: error.message || 'Failed to duplicate workflow' }
    }
  }
}
