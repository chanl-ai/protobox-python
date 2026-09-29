import { useAuth } from "@/lib/auth"
import { useAuthStore } from "@/lib/auth/stores/auth.store"

/**
 * Centralized hook to determine if workspace and auth are ready for API calls.
 * 
 * This prevents race conditions where pages try to make API calls with:
 * - undefined/null workspace IDs
 * - "loading" placeholder workspace IDs
 * - missing authentication tokens
 * 
 * NOTE: With the new ProtoboxClient, workspace-scoped API calls automatically
 * use the current workspace context. This hook is still useful for:
 * - Conditional rendering based on workspace readiness
 * - Validating workspace matches URL params
 * - Getting workspaceId for non-API operations
 * 
 * For API calls, prefer using useProtobox() hooks which handle workspace
 * context automatically.
 * 
 * @returns Object with readiness state and workspace info
 */
export function useWorkspaceReady() {
  const { user, isAuthenticated } = useAuth()
  const { 
    currentWorkspace, 
    workspaceLoading, 
    error 
  } = useAuthStore()
  
  // Check all conditions that must be met before making API calls
  const isAuthReady = isAuthenticated && Boolean(user?.customToken)
  const isWorkspaceLoaded = !workspaceLoading
  const hasValidWorkspaceId = Boolean(
    currentWorkspace?.id && 
    currentWorkspace.id !== "loading" && 
    currentWorkspace.id !== "default"
  )
  
  // Overall readiness - all conditions must be true AND no errors
  const isReady = isAuthReady && isWorkspaceLoaded && hasValidWorkspaceId && !error
  
  return {
    // Primary state
    isReady,
    workspaceId: currentWorkspace?.id || null,
    
    // Detailed state for debugging/conditional logic
    isAuthReady,
    isWorkspaceLoaded,
    hasValidWorkspaceId,
    workspaceLoading,
    error: error?.message || null,
    
    // Convenience access to workspace and user
    currentWorkspace,
    user,
    isAuthenticated,
    
    // Helper method for useEffect dependencies
    getDependencies: () => [user?.customToken, currentWorkspace?.id, workspaceLoading, error]
  }
}