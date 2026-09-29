/**
 * Query Key Factory for React Query
 * 
 * Provides type-safe, hierarchical query keys for cache management.
 * This ensures consistent key structure and easy cache invalidation.
 */

/**
 * Workspace query keys
 */
export const workspaceKeys = {
  all: ['workspaces'] as const,
  lists: () => [...workspaceKeys.all, 'list'] as const,
  list: (filters?: string) => [...workspaceKeys.lists(), { filters }] as const,
  details: () => [...workspaceKeys.all, 'detail'] as const,
  detail: (id: string) => [...workspaceKeys.details(), id] as const,
  settings: (id: string) => [...workspaceKeys.detail(id), 'settings'] as const,
  members: (id: string) => [...workspaceKeys.detail(id), 'members'] as const,
  stats: (id: string) => [...workspaceKeys.detail(id), 'stats'] as const,
}

/**
 * Actions query keys (workspace-scoped)
 */
export const actionKeys = {
  all: (workspaceId: string) => ['actions', workspaceId] as const,
  lists: (workspaceId: string) => [...actionKeys.all(workspaceId), 'list'] as const,
  list: (workspaceId: string, filters?: { type?: string; status?: string; tags?: string[] }) =>
    [...actionKeys.lists(workspaceId), { filters }] as const,
  details: (workspaceId: string) => [...actionKeys.all(workspaceId), 'detail'] as const,
  detail: (workspaceId: string, actionId: string) =>
    [...actionKeys.details(workspaceId), actionId] as const,
  files: (workspaceId: string, actionId: string) =>
    [...actionKeys.detail(workspaceId, actionId), 'files'] as const,
  types: (workspaceId: string) => [...actionKeys.all(workspaceId), 'types'] as const,
}

/**
 * Secrets query keys (workspace-scoped)
 */
export const secretKeys = {
  all: (workspaceId: string) => ['secrets', workspaceId] as const,
  lists: (workspaceId: string) => [...secretKeys.all(workspaceId), 'list'] as const,
  list: (workspaceId: string, filters?: { secret_type?: string; is_active?: boolean }) =>
    [...secretKeys.lists(workspaceId), { filters }] as const,
  details: (workspaceId: string) => [...secretKeys.all(workspaceId), 'detail'] as const,
  detail: (workspaceId: string, secretId: string) =>
    [...secretKeys.details(workspaceId), secretId] as const,
  types: (workspaceId: string) => [...secretKeys.all(workspaceId), 'types'] as const,
  usageLogs: (workspaceId: string, secretId: string) =>
    [...secretKeys.detail(workspaceId, secretId), 'usage-logs'] as const,
}

/**
 * Executions query keys (workspace-scoped)
 */
export const executionKeys = {
  all: (workspaceId: string) => ['executions', workspaceId] as const,
  lists: (workspaceId: string) => [...executionKeys.all(workspaceId), 'list'] as const,
  list: (
    workspaceId: string,
    filters?: {
      status?: string
      action_id?: string
      limit?: number
      offset?: number
      start_date?: string
      end_date?: string
    }
  ) => [...executionKeys.lists(workspaceId), { filters }] as const,
  details: (workspaceId: string) => [...executionKeys.all(workspaceId), 'detail'] as const,
  detail: (workspaceId: string, executionId: string) =>
    [...executionKeys.details(workspaceId), executionId] as const,
}

/**
 * User query keys
 */
export const userKeys = {
  all: ['users'] as const,
  profile: () => [...userKeys.all, 'profile'] as const,
  preferences: () => [...userKeys.all, 'preferences'] as const,
  lastWorkspace: () => [...userKeys.all, 'last-workspace'] as const,
}

/**
 * Integrations query keys (workspace-scoped)
 */
export const integrationKeys = {
  all: (workspaceId: string) => ['integrations', workspaceId] as const,
  lists: (workspaceId: string) => [...integrationKeys.all(workspaceId), 'list'] as const,
  list: (workspaceId: string) => [...integrationKeys.lists(workspaceId)] as const,
  available: () => ['integrations', 'available'] as const,
  detail: (workspaceId: string, integrationType: string) =>
    [...integrationKeys.all(workspaceId), integrationType] as const,
  tools: (workspaceId: string, integrationType: string) =>
    [...integrationKeys.detail(workspaceId, integrationType), 'tools'] as const,
}

/**
 * Knowledge base query keys (workspace-scoped)
 */
export const knowledgeKeys = {
  all: (workspaceId: string) => ['knowledge', workspaceId] as const,
  lists: (workspaceId: string) => [...knowledgeKeys.all(workspaceId), 'list'] as const,
  list: (workspaceId: string) => [...knowledgeKeys.lists(workspaceId)] as const,
  details: (workspaceId: string) => [...knowledgeKeys.all(workspaceId), 'detail'] as const,
  detail: (workspaceId: string, documentId: string) =>
    [...knowledgeKeys.details(workspaceId), documentId] as const,
  query: (workspaceId: string, query: string, filters?: any) =>
    [...knowledgeKeys.all(workspaceId), 'query', { query, filters }] as const,
  tasks: (workspaceId: string) => [...knowledgeKeys.all(workspaceId), 'tasks'] as const,
  task: (workspaceId: string, taskId: string) =>
    [...knowledgeKeys.tasks(workspaceId), taskId] as const,
}

/**
 * Assistants query keys (workspace-scoped)
 */
export const assistantKeys = {
  all: (workspaceId: string) => ['assistants', workspaceId] as const,
  lists: (workspaceId: string) => [...assistantKeys.all(workspaceId), 'list'] as const,
  list: (workspaceId: string) => [...assistantKeys.lists(workspaceId)] as const,
  details: (workspaceId: string) => [...assistantKeys.all(workspaceId), 'detail'] as const,
  detail: (workspaceId: string, assistantId: string) =>
    [...assistantKeys.details(workspaceId), assistantId] as const,
  default: (workspaceId: string) => [...assistantKeys.all(workspaceId), 'default'] as const,
  threads: (workspaceId: string, assistantId: string) =>
    [...assistantKeys.detail(workspaceId, assistantId), 'threads'] as const,
  messages: (workspaceId: string, threadId: string) =>
    [...assistantKeys.all(workspaceId), 'threads', threadId, 'messages'] as const,
}

/**
 * Stats query keys (workspace-scoped)
 */
export const statsKeys = {
  all: (workspaceId: string) => ['stats', workspaceId] as const,
  workspace: (workspaceId: string) => [...statsKeys.all(workspaceId), 'workspace'] as const,
  tokens: (workspaceId: string) => [...statsKeys.all(workspaceId), 'tokens'] as const,
}

/**
 * Consolidated query keys object for easy access
 */
export const queryKeys = {
  workspaces: workspaceKeys,
  actions: actionKeys,
  secrets: secretKeys,
  executions: executionKeys,
  users: userKeys,
  integrations: integrationKeys,
  knowledge: knowledgeKeys,
  assistants: assistantKeys,
  stats: statsKeys,
}

