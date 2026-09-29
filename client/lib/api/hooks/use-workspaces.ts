/**
 * useWorkspaces - Hook for workspace management
 * 
 * Provides workspace queries and mutations with optimistic updates
 */

'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { protoboxClient } from '../protobox-client'
import { queryKeys } from '../query-keys'
import type { Workspace } from '@/lib/auth/stores/auth.store'

/**
 * Hook for fetching workspaces list
 */
export function useWorkspaces() {
  return useQuery({
    queryKey: queryKeys.workspaces.list(),
    queryFn: async () => {
      const response = await protoboxClient.getWorkspaces()
      if (response.error) throw new Error(response.error)
      return response.data
    },
  })
}

/**
 * Hook for fetching single workspace
 */
export function useWorkspace(workspaceId: string) {
  return useQuery({
    queryKey: queryKeys.workspaces.detail(workspaceId),
    queryFn: async () => {
      const response = await protoboxClient.getWorkspace(workspaceId)
      if (response.error) throw new Error(response.error)
      return response.data
    },
    enabled: !!workspaceId,
  })
}

/**
 * Hook for creating workspace with optimistic update
 */
export function useCreateWorkspace() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: { name: string; slug?: string; description?: string; [key: string]: any }) => {
      const response = await protoboxClient.createWorkspace(data)
      if (response.error) throw new Error(response.error)
      return response.data
    },
    onSuccess: (newWorkspace) => {
      // Invalidate and refetch workspaces list
      queryClient.invalidateQueries({ queryKey: queryKeys.workspaces.lists() })
      
      // Optionally set the new workspace in cache
      if (newWorkspace?._id) {
        queryClient.setQueryData(queryKeys.workspaces.detail(newWorkspace._id), newWorkspace)
      }
    },
  })
}

/**
 * Hook for updating workspace with optimistic update
 */
export function useUpdateWorkspace() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ workspaceId, data }: { workspaceId: string; data: any }) => {
      const response = await protoboxClient.updateWorkspace(workspaceId, data)
      if (response.error) throw new Error(response.error)
      return response.data
    },
    onMutate: async ({ workspaceId, data }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.workspaces.detail(workspaceId) })

      // Snapshot previous value
      const previousWorkspace = queryClient.getQueryData<Workspace>(
        queryKeys.workspaces.detail(workspaceId)
      )

      // Optimistically update
      if (previousWorkspace) {
        queryClient.setQueryData<Workspace>(
          queryKeys.workspaces.detail(workspaceId),
          { ...previousWorkspace, ...data }
        )
      }

      return { previousWorkspace }
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previousWorkspace) {
        queryClient.setQueryData(
          queryKeys.workspaces.detail(variables.workspaceId),
          context.previousWorkspace
        )
      }
    },
    onSettled: (data, error, variables) => {
      // Refetch after mutation
      queryClient.invalidateQueries({ queryKey: queryKeys.workspaces.detail(variables.workspaceId) })
      queryClient.invalidateQueries({ queryKey: queryKeys.workspaces.lists() })
    },
  })
}

/**
 * Hook for deleting workspace
 */
export function useDeleteWorkspace() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (workspaceId: string) => {
      const response = await protoboxClient.deleteWorkspace(workspaceId)
      if (response.error) throw new Error(response.error)
      return response.data
    },
    onSuccess: (_, workspaceId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: queryKeys.workspaces.detail(workspaceId) })
      // Invalidate list
      queryClient.invalidateQueries({ queryKey: queryKeys.workspaces.lists() })
    },
  })
}

