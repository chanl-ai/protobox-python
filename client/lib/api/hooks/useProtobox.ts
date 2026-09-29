/**
 * useProtobox - Main hook for accessing all Protobox API resources
 * 
 * Provides standardized { data, loading, error, refetch } structure
 * for all API resources using React Query.
 * 
 * Usage:
 * ```tsx
 * const { workspaces, actions, secrets } = useProtobox()
 * // workspaces.data, workspaces.loading, workspaces.error
 * ```
 */

'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { protoboxClient } from '../protobox-client'
import { queryKeys } from '../query-keys'
import { useAuthStore } from '@/lib/auth/stores/auth.store'

/**
 * Standardized query result structure
 */
export interface QueryResult<T> {
  data: T | undefined
  loading: boolean
  error: Error | null
  refetch: () => void
  isRefetching: boolean
}

/**
 * Main useProtobox hook
 * Provides access to all API resources
 */
export function useProtobox() {
  const queryClient = useQueryClient()
  const { currentWorkspace } = useAuthStore()
  const workspaceId = currentWorkspace?._id

  // Workspaces
  const workspaces = useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: async () => {
      const response = await protoboxClient.getWorkspaces()
      if (response.error) throw new Error(response.error)
      return response.data
    },
    enabled: true, // Always enabled (user-scoped, not workspace-scoped)
  })

  // Actions (workspace-scoped)
  const actions = useQuery({
    queryKey: queryKeys.actions.list(workspaceId || ''),
    queryFn: async () => {
      if (!workspaceId) throw new Error('No workspace selected')
      const response = await protoboxClient.getActions(workspaceId)
      if (response.error) throw new Error(response.error)
      return response.data || []
    },
    enabled: !!workspaceId,
  })

  // Secrets (workspace-scoped)
  const secrets = useQuery({
    queryKey: queryKeys.secrets.list(workspaceId || ''),
    queryFn: async () => {
      if (!workspaceId) throw new Error('No workspace selected')
      const response = await protoboxClient.getSecrets(workspaceId)
      if (response.error) throw new Error(response.error)
      return response.data || []
    },
    enabled: !!workspaceId,
  })

  // Executions (workspace-scoped)
  const executions = useQuery({
    queryKey: queryKeys.executions.list(workspaceId || ''),
    queryFn: async () => {
      if (!workspaceId) throw new Error('No workspace selected')
      const response = await protoboxClient.getExecutions(workspaceId)
      if (response.error) throw new Error(response.error)
      return response.data || []
    },
    enabled: !!workspaceId,
  })

  // User profile
  const userProfile = useQuery({
    queryKey: queryKeys.users.profile(),
    queryFn: async () => {
      const response = await protoboxClient.getUserProfile()
      if (response.error) throw new Error(response.error)
      return response.data
    },
    enabled: true,
  })

  // Helper to transform React Query result to standardized format
  const toQueryResult = <T,>(
    query: ReturnType<typeof useQuery<T, Error>>
  ): QueryResult<T> => ({
    data: query.data,
    loading: query.isLoading,
    error: query.error,
    refetch: () => query.refetch(),
    isRefetching: query.isRefetching,
  })

  return {
    // Workspaces
    workspaces: toQueryResult(workspaces),

    // Workspace-scoped resources
    actions: toQueryResult(actions),
    secrets: toQueryResult(secrets),
    executions: toQueryResult(executions),

    // User resources
    userProfile: toQueryResult(userProfile),

    // Current workspace ID (for convenience)
    workspaceId,

    // Query client (for advanced usage)
    queryClient,
  }
}

