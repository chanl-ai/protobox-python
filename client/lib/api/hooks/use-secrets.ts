/**
 * useSecrets - Hook for secret management
 * 
 * Provides secret queries and mutations with optimistic updates
 */

'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { protoboxClient } from '../protobox-client'
import { queryKeys } from '../query-keys'
import { useAuthStore } from '@/lib/auth/stores/auth.store'

export interface Secret {
  id: string
  name: string
  description?: string
  secret_type: string
  secret_value?: string
  tags?: string[]
  is_active: boolean
  created_at: string
  updated_at: string
  expires_at?: string
  usage_count: number
  max_usage_count?: number
}

/**
 * Hook for fetching secrets list
 */
export function useSecrets(workspaceId?: string, filters?: { secret_type?: string; is_active?: boolean }) {
  const { currentWorkspace } = useAuthStore()
  const wsId = workspaceId || currentWorkspace?._id

  return useQuery({
    queryKey: queryKeys.secrets.list(wsId || '', filters),
    queryFn: async () => {
      if (!wsId) throw new Error('No workspace selected')
      const response = await protoboxClient.getSecrets(wsId, filters)
      if (response.error) throw new Error(response.error)
      return (response.data || []) as Secret[]
    },
    enabled: !!wsId,
  })
}

/**
 * Hook for fetching single secret
 */
export function useSecret(workspaceId: string | undefined, secretId: string) {
  const { currentWorkspace } = useAuthStore()
  const wsId = workspaceId || currentWorkspace?._id

  return useQuery({
    queryKey: queryKeys.secrets.detail(wsId || '', secretId),
    queryFn: async () => {
      if (!wsId) throw new Error('No workspace selected')
      const response = await protoboxClient.getSecret(wsId, secretId)
      if (response.error) throw new Error(response.error)
      return response.data as Secret
    },
    enabled: !!wsId && !!secretId,
  })
}

/**
 * Hook for creating secret with optimistic update
 */
export function useCreateSecret() {
  const queryClient = useQueryClient()
  const { currentWorkspace } = useAuthStore()
  const workspaceId = currentWorkspace?._id

  return useMutation({
    mutationFn: async (data: Omit<Secret, 'id' | 'created_at' | 'updated_at' | 'usage_count'>) => {
      if (!workspaceId) throw new Error('No workspace selected')
      const response = await protoboxClient.createSecret(workspaceId, data)
      if (response.error) throw new Error(response.error)
      return response.data as Secret
    },
    onMutate: async (newSecret) => {
      if (!workspaceId) return { previousSecrets: undefined }

      await queryClient.cancelQueries({ queryKey: queryKeys.secrets.lists(workspaceId) })

      const previousSecrets = queryClient.getQueryData<Secret[]>(
        queryKeys.secrets.list(workspaceId)
      )

      const optimisticSecret: Secret = {
        ...newSecret,
        id: 'temp-' + Date.now(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        usage_count: 0,
      }

      queryClient.setQueryData<Secret[]>(
        queryKeys.secrets.list(workspaceId),
        (old) => [...(old || []), optimisticSecret]
      )

      return { previousSecrets }
    },
    onError: (err, newSecret, context) => {
      if (workspaceId && context?.previousSecrets) {
        queryClient.setQueryData(
          queryKeys.secrets.list(workspaceId),
          context.previousSecrets
        )
      }
    },
    onSuccess: (data) => {
      if (workspaceId) {
        queryClient.setQueryData<Secret[]>(
          queryKeys.secrets.list(workspaceId),
          (old) => {
            if (!old) return [data]
            return old.map((secret) =>
              secret.id.startsWith('temp-') ? data : secret
            )
          }
        )
        queryClient.setQueryData(queryKeys.secrets.detail(workspaceId, data.id), data)
      }
    },
    onSettled: () => {
      if (workspaceId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.secrets.lists(workspaceId) })
      }
    },
  })
}

/**
 * Hook for updating secret with optimistic update
 */
export function useUpdateSecret() {
  const queryClient = useQueryClient()
  const { currentWorkspace } = useAuthStore()
  const workspaceId = currentWorkspace?._id

  return useMutation({
    mutationFn: async ({ secretId, data }: { secretId: string; data: Partial<Secret> }) => {
      if (!workspaceId) throw new Error('No workspace selected')
      const response = await protoboxClient.updateSecret(workspaceId, secretId, data)
      if (response.error) throw new Error(response.error)
      return response.data as Secret
    },
    onMutate: async ({ secretId, data }) => {
      if (!workspaceId) return { previousSecret: undefined, previousSecrets: undefined }

      await queryClient.cancelQueries({ queryKey: queryKeys.secrets.detail(workspaceId, secretId) })
      await queryClient.cancelQueries({ queryKey: queryKeys.secrets.lists(workspaceId) })

      const previousSecret = queryClient.getQueryData<Secret>(
        queryKeys.secrets.detail(workspaceId, secretId)
      )
      const previousSecrets = queryClient.getQueryData<Secret[]>(
        queryKeys.secrets.list(workspaceId)
      )

      if (previousSecret) {
        queryClient.setQueryData<Secret>(
          queryKeys.secrets.detail(workspaceId, secretId),
          { ...previousSecret, ...data, updated_at: new Date().toISOString() }
        )
      }

      if (previousSecrets) {
        queryClient.setQueryData<Secret[]>(
          queryKeys.secrets.list(workspaceId),
          (old) =>
            old?.map((secret) =>
              secret.id === secretId
                ? { ...secret, ...data, updated_at: new Date().toISOString() }
                : secret
            ) || []
        )
      }

      return { previousSecret, previousSecrets }
    },
    onError: (err, variables, context) => {
      if (workspaceId) {
        if (context?.previousSecret) {
          queryClient.setQueryData(
            queryKeys.secrets.detail(workspaceId, variables.secretId),
            context.previousSecret
          )
        }
        if (context?.previousSecrets) {
          queryClient.setQueryData(
            queryKeys.secrets.list(workspaceId),
            context.previousSecrets
          )
        }
      }
    },
    onSuccess: (data) => {
      if (workspaceId) {
        queryClient.setQueryData(queryKeys.secrets.detail(workspaceId, data.id), data)
        queryClient.setQueryData<Secret[]>(
          queryKeys.secrets.list(workspaceId),
          (old) => old?.map((secret) => (secret.id === data.id ? data : secret)) || []
        )
      }
    },
    onSettled: (data, error, variables) => {
      if (workspaceId) {
        queryClient.invalidateQueries({ queryKey: queryKeys.secrets.detail(workspaceId, variables.secretId) })
        queryClient.invalidateQueries({ queryKey: queryKeys.secrets.lists(workspaceId) })
      }
    },
  })
}

/**
 * Hook for deleting secret
 */
export function useDeleteSecret() {
  const queryClient = useQueryClient()
  const { currentWorkspace } = useAuthStore()
  const workspaceId = currentWorkspace?._id

  return useMutation({
    mutationFn: async (secretId: string) => {
      if (!workspaceId) throw new Error('No workspace selected')
      const response = await protoboxClient.deleteSecret(workspaceId, secretId)
      if (response.error) throw new Error(response.error)
      return response.data
    },
    onMutate: async (secretId) => {
      if (!workspaceId) return { previousSecrets: undefined }

      await queryClient.cancelQueries({ queryKey: queryKeys.secrets.lists(workspaceId) })

      const previousSecrets = queryClient.getQueryData<Secret[]>(
        queryKeys.secrets.list(workspaceId)
      )

      queryClient.setQueryData<Secret[]>(
        queryKeys.secrets.list(workspaceId),
        (old) => old?.filter((secret) => secret.id !== secretId) || []
      )

      return { previousSecrets }
    },
    onError: (err, secretId, context) => {
      if (workspaceId && context?.previousSecrets) {
        queryClient.setQueryData(
          queryKeys.secrets.list(workspaceId),
          context.previousSecrets
        )
      }
    },
    onSuccess: (_, secretId) => {
      if (workspaceId) {
        queryClient.removeQueries({ queryKey: queryKeys.secrets.detail(workspaceId, secretId) })
        queryClient.invalidateQueries({ queryKey: queryKeys.secrets.lists(workspaceId) })
      }
    },
  })
}

