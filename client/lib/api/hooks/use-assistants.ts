'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { protoboxClient } from '../protobox-client'
import { queryKeys } from '../query-keys'
import { useAuthStore } from '@/lib/auth/stores/auth.store'

export interface Assistant {
  id: string
  name: string
  instructions: string
  model: string
  tools: any[]
  created_at?: string
  updated_at?: string
}

export interface Thread {
  id: string
  assistant_id: string
  created_at: string
  metadata?: {
    title?: string
    last_message?: string
  }
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  tool_calls?: any[]
}

/**
 * Hook for fetching default assistant
 */
export function useDefaultAssistant(workspaceId?: string) {
  const { currentWorkspace } = useAuthStore()
  const wsId = workspaceId || currentWorkspace?._id

  return useQuery({
    queryKey: queryKeys.assistants.default(wsId || ''),
    queryFn: async () => {
      if (!wsId) throw new Error('No workspace selected')
      const response = await protoboxClient.getOrCreateDefaultAssistant(wsId)
      if (response.error) throw new Error(response.error)
      return response.data as Assistant
    },
    enabled: !!wsId,
  })
}

/**
 * Hook for listing threads
 */
export function useThreads(workspaceId: string | undefined, assistantId: string) {
  const { currentWorkspace } = useAuthStore()
  const wsId = workspaceId || currentWorkspace?._id

  return useQuery({
    queryKey: queryKeys.assistants.threads(wsId || '', assistantId),
    queryFn: async () => {
      if (!wsId) throw new Error('No workspace selected')
      const response = await protoboxClient.listThreads(wsId, assistantId)
      if (response.error) throw new Error(response.error)
      return (response.data || []) as Thread[]
    },
    enabled: !!wsId && !!assistantId,
  })
}

/**
 * Hook for fetching messages
 */
export function useMessages(workspaceId: string | undefined, threadId: string, limit?: number) {
  const { currentWorkspace } = useAuthStore()
  const wsId = workspaceId || currentWorkspace?._id

  return useQuery({
    queryKey: queryKeys.assistants.messages(wsId || '', threadId),
    queryFn: async () => {
      if (!wsId) throw new Error('No workspace selected')
      const response = await protoboxClient.getMessages(wsId, threadId, limit)
      if (response.error) throw new Error(response.error)
      return (response.data || []) as Message[]
    },
    enabled: !!wsId && !!threadId,
  })
}

/**
 * Hook for creating a thread
 */
export function useCreateThread() {
  const queryClient = useQueryClient()
  const { currentWorkspace } = useAuthStore()
  const wsId = currentWorkspace?._id

  return useMutation({
    mutationFn: async ({ workspaceId, assistantId, data }: { workspaceId: string; assistantId: string; data: any }) => {
      const response = await protoboxClient.createThread(workspaceId, assistantId, data)
      if (response.error) throw new Error(response.error)
      return response.data as Thread
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.assistants.threads(variables.workspaceId, variables.assistantId) })
    },
  })
}

