import { useAuthStore } from '../stores/auth.store'

/**
 * Hook to access workspace state and methods
 * 
 * This hook provides backward compatibility for components migrating from WorkspaceProvider.
 * It wraps useAuthStore() to match the provider interface.
 * 
 * @deprecated For new code, use useAuthStore() directly instead.
 * This hook will be removed once all components are migrated.
 */
export function useWorkspace() {
  const {
    currentWorkspace,
    workspaces,
    workspaceLoading,
    error,
    selectWorkspace,
    createWorkspace,
    refreshWorkspaces,
  } = useAuthStore()
  
  // Compute isReady state (matches provider interface)
  const isReady = !workspaceLoading && !!currentWorkspace && !error
  
  // Map selectWorkspace to switchWorkspace for backward compatibility
  const switchWorkspace = async (workspaceId: string) => {
    await selectWorkspace(workspaceId)
  }
  
  // Map createWorkspace signature (provider expected addWorkspace with full workspace object)
  const addWorkspace = async (workspace: { name: string }) => {
    return await createWorkspace(workspace.name)
  }
  
  return {
    currentWorkspace,
    workspaces,
    loading: workspaceLoading,
    error: error?.message || null,
    isReady,
    switchWorkspace,
    addWorkspace,
    removeWorkspace: () => {
      // TODO: Implement workspace deletion in auth store
      console.warn('Workspace deletion not yet implemented')
    },
    refreshWorkspaces,
  }
}