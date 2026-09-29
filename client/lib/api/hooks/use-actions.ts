/**
 * useActions - Hook for action management
 * 
 * Provides action queries and mutations with optimistic updates
 */

'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { protoboxClient } from '../protobox-client'
import { queryKeys } from '../query-keys'
import { useAuthStore } from '@/lib/auth/stores/auth.store'

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
  status?: string
  is_builtin?: boolean
  secret_refs?: string[]
  created_by: string
  created_at: string
  updated_at: string
}

/**
 * Hook for fetching actions list
 */
export function useActions(workspaceId?: string, filters?: { type?: string; status?: string; tags?: string[] }) {
  const { currentWorkspace } = useAuthStore()
  const wsId = workspaceId || currentWorkspace?._id

  return useQuery({
    queryKey: queryKeys.actions.list(wsId || '', filters),
    queryFn: async () => {
      if (!wsId) throw new Error('No workspace selected')
      const response = await protoboxClient.getActions(wsId, filters)
      if (response.error) throw new Error(response.error)
      return (response.data || []) as Action[]
    },
    enabled: !!wsId,
  })
}

/**
 * Hook for fetching single action
 */
export function useAction(workspaceId: string | undefined, actionId: string) {
  const { currentWorkspace } = useAuthStore()
  const wsId = workspaceId || currentWorkspace?._id

  return useQuery({
    queryKey: queryKeys.actions.detail(wsId || '', actionId),
    queryFn: async () => {
      if (!wsId) throw new Error('No workspace selected')
      const response = await protoboxClient.getAction(wsId, actionId)
      if (response.error) throw new Error(response.error)
      return response.data as Action
    },
    enabled: !!wsId && !!actionId,
  })
}

/**
 * Hook for creating action with optimistic update
 */
export function useCreateAction() {
  const queryClient = useQueryClient()
  const { currentWorkspace } = useAuthStore()
  const workspaceId = currentWorkspace?._id

  return useMutation({
    mutationFn: async (data: Omit<Action, 'id' | 'workspace_id' | 'created_by' | 'created_at' | 'updated_at'>) => {
      if (!workspaceId) throw new Error('No workspace selected')
      const response = await protoboxClient.createAction(workspaceId, data)
      if (response.error) throw new Error(response.error)
      return response.data as Action
    },
    onMutate: async (newAction) => {
      if (!workspaceId) return { previousActions: undefined }

      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.actions.lists(workspaceId) })

      // Snapshot previous value
      const previousActions = queryClient.getQueryData<Action[]>(
        queryKeys.actions.list(workspaceId)
      )

      // Optimistically update
      const optimisticAction: Action = {
        ...newAction,
        id: 'temp-' + Date.now(),
        workspace_id: workspaceId,
        created_by: 'current-user', // Will be replaced by server
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }

      queryClient.setQueryData<Action[]>(
        queryKeys.actions.list(workspaceId),
        (old) => [...(old || []), optimisticAction]
      )

      return { previousActions }
    },
    onError: (err, newAction, context) => {
      // Rollback on error
      if (workspaceId && context?.previousActions) {
        queryClient.setQueryData(
          queryKeys.actions.list(workspaceId),
          context.previousActions
        )
      }
    },
    onSuccess: (data) => {
      // Replace optimistic action with real one
      if (workspaceId) {
        queryClient.setQueryData<Action[]>(
          queryKeys.actions.list(workspaceId),
          (old) => {
            if (!old) return [data]
            return old.map((action) =>
              action.id.startsWith('temp-') ? data : action
            )
          }
        )
        // Set detail cache
        queryClient.setQueryData(queryKeys.actions.detail(workspaceId, data.id), data)
      }
    },
    onSettled: () => {
      // Refetch to ensure consistency
      if (workspaceId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.actions.lists(workspaceId) })
      }
    },
  })
}

/**
 * Hook for updating action with optimistic update
 */
export function useUpdateAction() {
  const queryClient = useQueryClient()
  const { currentWorkspace } = useAuthStore()
  const workspaceId = currentWorkspace?._id

  return useMutation({
    mutationFn: async ({ actionId, data }: { actionId: string; data: Partial<Action> }) => {
      if (!workspaceId) throw new Error('No workspace selected')
      const response = await protoboxClient.updateAction(workspaceId, actionId, data)
      if (response.error) throw new Error(response.error)
      return response.data as Action
    },
    onMutate: async ({ actionId, data }) => {
      if (!workspaceId) return { previousAction: undefined, previousActions: undefined }

      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.actions.detail(workspaceId, actionId) })
      await queryClient.cancelQueries({ queryKey: queryKeys.actions.lists(workspaceId) })

      // Snapshot previous values
      const previousAction = queryClient.getQueryData<Action>(
        queryKeys.actions.detail(workspaceId, actionId)
      )
      const previousActions = queryClient.getQueryData<Action[]>(
        queryKeys.actions.list(workspaceId)
      )

      // Optimistically update detail
      if (previousAction) {
        queryClient.setQueryData<Action>(
          queryKeys.actions.detail(workspaceId, actionId),
          { ...previousAction, ...data, updated_at: new Date().toISOString() }
        )
      }

      // Optimistically update list
      if (previousActions) {
        queryClient.setQueryData<Action[]>(
          queryKeys.actions.list(workspaceId),
          (old) =>
            old?.map((action) =>
              action.id === actionId
                ? { ...action, ...data, updated_at: new Date().toISOString() }
                : action
            ) || []
        )
      }

      return { previousAction, previousActions }
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (workspaceId) {
        if (context?.previousAction) {
          queryClient.setQueryData(
            queryKeys.actions.detail(workspaceId, variables.actionId),
            context.previousAction
          )
        }
        if (context?.previousActions) {
          queryClient.setQueryData(
            queryKeys.actions.list(workspaceId),
            context.previousActions
          )
        }
      }
    },
    onSuccess: (data) => {
      // Update with server response
      if (workspaceId) {
        queryClient.setQueryData(queryKeys.actions.detail(workspaceId, data.id), data)
        queryClient.setQueryData<Action[]>(
          queryKeys.actions.list(workspaceId),
          (old) => old?.map((action) => (action.id === data.id ? data : action)) || []
        )
      }
    },
    onSettled: (data, error, variables) => {
      // Refetch to ensure consistency
      if (workspaceId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.actions.detail(workspaceId, variables.actionId) })
        queryClient.invalidateQueries({ queryKey: queryKeys.actions.lists(workspaceId) })
      }
    },
  })
}

/**
 * Hook for deleting action
 */
export function useDeleteAction() {
  const queryClient = useQueryClient()
  const { currentWorkspace } = useAuthStore()
  const workspaceId = currentWorkspace?._id

  return useMutation({
    mutationFn: async (actionId: string) => {
      if (!workspaceId) throw new Error('No workspace selected')
      const response = await protoboxClient.deleteAction(workspaceId, actionId)
      if (response.error) throw new Error(response.error)
      return response.data
    },
    onMutate: async (actionId) => {
      if (!workspaceId) return { previousActions: undefined }

      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.actions.lists(workspaceId) })

      // Snapshot previous value
      const previousActions = queryClient.getQueryData<Action[]>(
        queryKeys.actions.list(workspaceId)
      )

      // Optimistically remove
      queryClient.setQueryData<Action[]>(
        queryKeys.actions.list(workspaceId),
        (old) => old?.filter((action) => action.id !== actionId) || []
      )

      return { previousActions }
    },
    onError: (err, actionId, context) => {
      // Rollback on error
      if (workspaceId && context?.previousActions) {
        queryClient.setQueryData(
          queryKeys.actions.list(workspaceId),
          context.previousActions
        )
      }
    },
    onSuccess: (_, actionId) => {
      // Remove from cache
      if (workspaceId) {
        queryClient.removeQueries({ queryKey: queryKeys.actions.detail(workspaceId, actionId) })
        queryClient.invalidateQueries({ queryKey: queryKeys.actions.lists(workspaceId) })
      }
    },
  })
}

