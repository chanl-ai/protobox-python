/**
 * useExecutions - Hook for execution management
 * 
 * Provides execution queries and mutations with optimistic updates
 */

'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { protoboxClient } from '../protobox-client'
import { queryKeys } from '../query-keys'
import { useAuthStore } from '@/lib/auth/stores/auth.store'

export interface Execution {
  id: string
  workspace_id: string
  action_id: string
  action_name?: string
  status: string
  input?: any
  output?: any
  output_data?: any
  error?: string
  error_message?: string
  started_at: string
  completed_at?: string
  duration_ms?: number
  execution_time_ms?: number
  user_id?: string
  user_name?: string
  created_at: string
  updated_at: string
}

/**
 * Hook for fetching executions list
 */
export function useExecutions(
  workspaceId?: string,
  filters?: {
    status?: string
    action_id?: string
    limit?: number
    offset?: number
    start_date?: string
    end_date?: string
  }
) {
  const { currentWorkspace } = useAuthStore()
  const wsId = workspaceId || currentWorkspace?._id

  return useQuery({
    queryKey: queryKeys.executions.list(wsId || '', filters),
    queryFn: async () => {
      if (!wsId) throw new Error('No workspace selected')
      const response = await protoboxClient.getExecutions(wsId, filters)
      if (response.error) throw new Error(response.error)
      return (response.data || []) as Execution[]
    },
    enabled: !!wsId,
  })
}

/**
 * Hook for fetching single execution
 */
export function useExecution(workspaceId?: string, executionId?: string) {
  const { currentWorkspace } = useAuthStore()
  const wsId = workspaceId || currentWorkspace?._id

  return useQuery({
    queryKey: queryKeys.executions.detail(wsId || '', executionId || ''),
    queryFn: async () => {
      if (!wsId) throw new Error('No workspace selected')
      if (!executionId) throw new Error('No execution ID provided')
      const response = await protoboxClient.getExecution(wsId, executionId)
      if (response.error) throw new Error(response.error)
      return response.data as Execution
    },
    enabled: !!wsId && !!executionId,
  })
}

/**
 * Hook for canceling execution
 */
export function useCancelExecution() {
  const queryClient = useQueryClient()
  const { currentWorkspace } = useAuthStore()

  return useMutation({
    mutationFn: async ({ executionId }: { executionId: string }) => {
      if (!currentWorkspace?._id) throw new Error('No workspace selected')
      const response = await protoboxClient.cancelExecution(currentWorkspace._id, executionId)
      if (response.error) throw new Error(response.error)
      return response.data
    },
    onSuccess: (_, variables) => {
      // Invalidate executions list
      queryClient.invalidateQueries({
        queryKey: queryKeys.executions.all(currentWorkspace?._id || ''),
      })
    },
  })
}

/**
 * Hook for retrying execution
 */
export function useRetryExecution() {
  const queryClient = useQueryClient()
  const { currentWorkspace } = useAuthStore()

  return useMutation({
    mutationFn: async ({ executionId }: { executionId: string }) => {
      if (!currentWorkspace?._id) throw new Error('No workspace selected')
      const response = await protoboxClient.retryExecution(currentWorkspace._id, executionId)
      if (response.error) throw new Error(response.error)
      return response.data
    },
    onSuccess: (_, variables) => {
      // Invalidate executions list
      queryClient.invalidateQueries({
        queryKey: queryKeys.executions.all(currentWorkspace?._id || ''),
      })
    },
  })
}

