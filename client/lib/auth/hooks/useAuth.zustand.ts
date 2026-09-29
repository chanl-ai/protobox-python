import { useAuthStore } from '../stores/auth.store'

/**
 * Hook to access authentication state and methods using Zustand
 * This now uses the unified auth store for better integration
 */
export function useAuth() {
  const {
    user,
    authLoading,
    tokenLoading,
    workspaceLoading,
    error,
    isAuthenticated,
    currentWorkspace,
    workspaces,
    signIn,
    signUp,
    signOut,
    signInWithGoogle,
    signInWithApple,
    signInWithFacebook,
    resetPassword,
    updatePassword,
    updateProfile,
    sendEmailVerification,
    loadWorkspaces,
    selectWorkspace,
    createWorkspace,
    refreshWorkspaces
  } = useAuthStore()
  
  // Combine loading states for backward compatibility
  const loading = authLoading || tokenLoading
  const initialized = !authLoading
  
  // Auth state tracking for development
  
  return {
    // Auth state
    user,
    loading,
    error,
    initialized,
    isAuthenticated,
    
    // Workspace state
    currentWorkspace,
    workspaces,
    workspaceLoading,
    
    // Auth methods
    signIn,
    signUp,
    signOut,
    signInWithGoogle,
    signInWithApple,
    signInWithFacebook,
    resetPassword,
    updatePassword,
    updateProfile,
    sendEmailVerification,
    
    // Workspace methods
    loadWorkspaces,
    selectWorkspace,
    createWorkspace,
    refreshWorkspaces
  }
}