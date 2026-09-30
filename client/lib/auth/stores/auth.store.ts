import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { 
  User,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  FacebookAuthProvider,
  OAuthProvider,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  sendPasswordResetEmail,
  sendEmailVerification,
  updatePassword,
  updateProfile
} from 'firebase/auth'
import { getFirebaseAuth, initializeFirebase } from '../utils/firebase'
import { FirebaseConfig } from '../types'
import { protoboxClient } from '@/lib/api/protobox-client'
import { loggers } from '@/lib/logger'
import { userStorage } from '../utils/user-storage'
import { tokenManager } from '../token-manager'

// Types
export interface Workspace {
  _id: string
  id: string
  name: string
  slug: string
  description?: string
  settings?: {
    needs_onboarding?: boolean
  }
  created_at: string
  updated_at: string
}

export interface AuthUser extends Partial<User> {
  customToken?: string
  workspaceId?: string
  db_id?: string
}

export interface AuthState {
  // Authentication state
  firebaseUser: User | null
  customToken: string | null
  isAuthenticated: boolean
  
  // User state
  user: AuthUser | null
  
  // Workspace state
  currentWorkspace: Workspace | null
  workspaces: Workspace[]
  
  // Loading states - granular for better UX
  authLoading: boolean
  tokenLoading: boolean
  workspaceLoading: boolean
  
  // Error state
  error: Error | null
  
  // Configuration
  initialized: boolean
  firebaseConfig: FirebaseConfig | null
  
  // Core auth actions
  initialize: (config: FirebaseConfig) => void
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string, displayName?: string) => Promise<void>
  signOut: () => Promise<void>
  signInWithGoogle: () => Promise<void>
  signInWithApple: () => Promise<void>
  signInWithFacebook: () => Promise<void>
  resetPassword: (email: string) => Promise<void>
  updatePassword: (newPassword: string) => Promise<void>
  updateProfile: (displayName: string) => Promise<void>
  sendEmailVerification: () => Promise<void>
  
  // Workspace actions
  loadWorkspaces: () => Promise<void>
  selectWorkspace: (workspaceId: string) => Promise<void>
  createWorkspace: (name: string) => Promise<Workspace>
  refreshWorkspaces: () => Promise<void>
  
  // Internal actions
  _handleAuthStateChange: (firebaseUser: User | null, skipWorkspaceReload?: boolean) => Promise<void>
  _exchangeTokenAndLoadWorkspaces: (firebaseUser: User) => Promise<void>
  _clearAuthState: () => void
}

// Helper function to set cookie (for better security)
const setCookie = (name: string, value: string, days: number = 30) => {
  if (typeof window === 'undefined') return
  
  const expires = new Date()
  expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000)
  
  // Only use Secure flag for HTTPS (production), not for localhost HTTP
  const isSecure = window.location.protocol === 'https:'
  const secureFlag = isSecure ? ';Secure' : ''
  
  // Note: HttpOnly can't be set from JavaScript - this needs server-side setting
  // This is a temporary solution until we implement proper server-side cookie handling
  document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Strict${secureFlag}`
}

const clearCookie = (name: string) => {
  if (typeof window === 'undefined') return
  document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;`
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      firebaseUser: null,
      customToken: null,
      isAuthenticated: false,
      user: null,
      currentWorkspace: null,
      workspaces: [],
      authLoading: true,
      tokenLoading: false,
      workspaceLoading: false,
      error: null,
      initialized: false,
      firebaseConfig: null,
      
      // Initialize Firebase and auth listener
      initialize: (config) => {
        const state = get()
        if (state.initialized) {
          return
        }
        
        try {
          initializeFirebase(config)
          
          set({ firebaseConfig: config, initialized: true })
          
          // Set up auth state listener
          const auth = getFirebaseAuth()
          const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
            await get()._handleAuthStateChange(firebaseUser)
          })
          
          // Store unsubscribe for cleanup if needed
          if (typeof window !== 'undefined') {
            (window as any).__authUnsubscribe = unsubscribe
            
            // Add visibility change listener with smart refresh strategy
            let focusTimeout: NodeJS.Timeout | null = null
            let isRefreshing = false
            let lastRefreshTime = Date.now()
            
            const handleVisibilityChange = async () => {
              if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
                // Clear any pending refresh
                if (focusTimeout) {
                  clearTimeout(focusTimeout)
                }
                
                // Debounce rapid tab switches (1 second)
                focusTimeout = setTimeout(async () => {
                  const currentUser = auth.currentUser
                  if (currentUser) {
                    try {
                      // Check if we actually need to refresh
                      const tokenResult = await currentUser.getIdTokenResult(false) // Don't force refresh yet
                      const expirationTime = new Date(tokenResult.expirationTime).getTime()
                      const now = Date.now()
                      const timeSinceLastRefresh = now - lastRefreshTime
                      
                      // Only refresh if:
                      // 1. Token expires in less than 5 minutes
                      // 2. OR it's been more than 30 minutes since last refresh
                      // 3. AND we're not already refreshing
                      const shouldRefresh = !isRefreshing && (
                        expirationTime < (now + 5 * 60 * 1000) || // Token expires in < 5 min
                        timeSinceLastRefresh > 30 * 60 * 1000     // Been > 30 min since refresh
                      )
                      
                      if (shouldRefresh) {
                        isRefreshing = true
                        console.log('🔄 Tab focus: Smart token refresh triggered')
                        // Only force refresh if actually needed
                        await currentUser.getIdToken(true)
                        lastRefreshTime = Date.now()
                        // Skip workspace reload on tab focus - just refresh the token
                        await get()._handleAuthStateChange(currentUser, true)
                        isRefreshing = false
                      } else {
                        console.log('⏭️ Tab focus: Skipping refresh (token still valid)')
                      }
                    } catch (error) {
                      isRefreshing = false
                      // Silently handle refresh failures - user can manually refresh if needed
                      if (process.env.NODE_ENV === 'development') {
                        console.debug('Tab focus refresh failed', error)
                      }
                      // Only clear auth state if it's a real auth error, not a network issue
                      if (error && typeof error === 'object' && 'code' in error && 
                          (error.code === 'auth/user-token-expired' || 
                           error.code === 'auth/user-disabled' ||
                           error.code === 'auth/user-not-found')) {
                        get()._clearAuthState()
                      }
                    }
                  } else if (state.firebaseUser) {
                    // We think we have a user but Firebase doesn't - clear stale state
                    get()._clearAuthState()
                  }
                }, 1000) // 1 second debounce
              }
            }
            
            if (typeof document !== 'undefined') {
              document.addEventListener('visibilitychange', handleVisibilityChange)
            }
            
            // Set up periodic token refresh (every 60 minutes while tab is visible)
            let refreshInterval: NodeJS.Timeout | null = null
            
            const startTokenRefreshInterval = () => {
              // Clear any existing interval
              if (refreshInterval) {
                clearInterval(refreshInterval)
              }
              
              // Only refresh if tab is visible
              if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
                refreshInterval = setInterval(async () => {
                  if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
                    const currentUser = auth.currentUser
                    if (currentUser) {
                      try {
                        // Check if token actually needs refresh before forcing it
                        const tokenResult = await currentUser.getIdTokenResult(false)
                        const expirationTime = new Date(tokenResult.expirationTime).getTime()
                        const now = Date.now()
                        
                        // Only refresh if token expires in less than 10 minutes
                        if (expirationTime < (now + 10 * 60 * 1000)) {
                          console.log('⏰ Periodic refresh: Token expiring soon, refreshing...')
                          await currentUser.getIdToken(true)
                          // Skip workspace reload on periodic refresh too
                          await get()._handleAuthStateChange(currentUser, true)
                        } else {
                          console.log('⏰ Periodic refresh: Token still valid, skipping')
                        }
                      } catch (error) {
                        // Ignore periodic refresh errors - they're not critical
                        if (process.env.NODE_ENV === 'development') {
                          console.debug('Periodic token refresh failed', error)
                        }
                      }
                    }
                  }
                }, 60 * 60 * 1000) // 60 minutes (increased from 30)
              }
            }
            
            // Start refresh interval
            startTokenRefreshInterval()
            
            // Restart interval when tab becomes visible
            const originalHandleVisibilityChange = handleVisibilityChange
            const enhancedHandleVisibilityChange = async () => {
              await originalHandleVisibilityChange()
              if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
                startTokenRefreshInterval()
              } else {
                // Stop refreshing when tab is hidden
                if (refreshInterval) {
                  clearInterval(refreshInterval)
                  refreshInterval = null
                }
              }
            }
            
            // Replace the event listener with enhanced version
            if (typeof document !== 'undefined') {
              document.removeEventListener('visibilitychange', handleVisibilityChange)
              document.addEventListener('visibilitychange', enhancedHandleVisibilityChange)
            }
            
            // Store cleanup function
            (window as any).__authCleanup = () => {
              if (typeof document !== 'undefined') {
                document.removeEventListener('visibilitychange', enhancedHandleVisibilityChange)
              }
              if (refreshInterval) {
                clearInterval(refreshInterval)
              }
              if ((window as any).__authUnsubscribe) {
                (window as any).__authUnsubscribe()
              }
            }
          }
        } catch (error) {
          console.error('[Auth Store] Initialization failed with error:', error)
          console.error('[Auth Store] Error type:', typeof error)
          console.error('[Auth Store] Error message:', error instanceof Error ? error.message : String(error))
          console.error('[Auth Store] Error stack:', error instanceof Error ? error.stack : 'No stack trace')
          
          loggers.auth.error('Initialization failed', { 
            error,
            errorType: typeof error,
            errorMessage: error instanceof Error ? error.message : String(error),
            config: config
          })
          set({ error: error as Error })
        }
      },
      
      // Handle auth state changes
      _handleAuthStateChange: async (firebaseUser, skipWorkspaceReload = false) => {
        const authChangeTime = performance.now()
        console.log('🔥 Firebase auth state change detected')
        
        if (!firebaseUser) {
          // User signed out
          console.log('👋 User signed out')
          get()._clearAuthState()
          return
        }
        
        // Check if this is the same user and we already have a valid token
        const state = get()
        const isSameUser = state.firebaseUser?.uid === firebaseUser.uid
        const hasValidToken = state.customToken && !state.error
        
        if (isSameUser && hasValidToken && skipWorkspaceReload) {
          console.log('⏭️ Same user with valid token, skipping full reload')
          // Just update the firebase user reference
          set({ firebaseUser })
          return
        }
        
        // User signed in - exchange token and load workspaces
        console.log('👤 User signed in, starting auth flow')
        set({ 
          firebaseUser, 
          authLoading: true,
          tokenLoading: true,
          workspaceLoading: !skipWorkspaceReload 
        })
        
        try {
          await get()._exchangeTokenAndLoadWorkspaces(firebaseUser)
        } catch (error) {
          // Silently handle auth flow errors - they're already logged in _exchangeTokenAndLoadWorkspaces
          set({ 
            error: error as Error,
            authLoading: false,
            tokenLoading: false,
            workspaceLoading: false
          })
        }
      },
      
      // Exchange token and load workspaces in one flow
      _exchangeTokenAndLoadWorkspaces: async (firebaseUser) => {
        const startTime = performance.now()
        console.log('🔄 Auth Flow: Starting token exchange and workspace loading')
        
        try {
          // Step 1: Exchange Firebase token for custom JWT
          const tokenStartTime = performance.now()
          set({ tokenLoading: true })
          const idToken = await firebaseUser.getIdToken()
          console.log(`⏱️ Auth Flow: Firebase getIdToken took ${(performance.now() - tokenStartTime).toFixed(2)}ms`)
          const exchangeStartTime = performance.now()
          const tokenResponse = await protoboxClient.exchangeToken(idToken)
          console.log(`⏱️ Auth Flow: Token exchange took ${(performance.now() - exchangeStartTime).toFixed(2)}ms`)
          
          if (!tokenResponse.data?.access_token) {
            throw new Error('No access token received from server')
          }
          
          // Store tokens
          const customToken = tokenResponse.data.access_token
          
          // IMPORTANT: Use tokenManager to set the token
          // This ensures it's available for all API calls immediately
          tokenManager.setToken(customToken)
          
          // Also set refresh token in cookie
          if (tokenResponse.data.refresh_token) {
            setCookie('refresh-token', tokenResponse.data.refresh_token)
          }
          
          // Create unified user object
          const user: AuthUser = {
            ...firebaseUser,
            customToken,
            db_id: tokenResponse.data.user?.db_id,
            workspaceId: tokenResponse.data.user?.workspace_id
          }
          
          set({ 
            customToken,
            user,
            isAuthenticated: true,
            tokenLoading: false
          })
          
          // Step 2: Load workspaces - Now pass the token explicitly
          const workspaceStartTime = performance.now()
          console.log(`⏱️ Auth Flow: Token setup complete, starting workspace loading`)
          set({ workspaceLoading: true })
          
          // Use the centralized API client which gets tokens from tokenManager
          // The API client will use the token from tokenManager automatically
          const response = await protoboxClient.getWorkspaces()
          
          if (response.error) {
            throw new Error(`Failed to load workspaces: ${response.error}`)
          }
          
          const workspacesResponse = response.data
          const workspaces = workspacesResponse?.workspaces || []
          const userLastWorkspaceId = workspacesResponse?.user?.last_workspace_id
          console.log(`⏱️ Auth Flow: Workspace loading took ${(performance.now() - workspaceStartTime).toFixed(2)}ms`)
          
          // Select current workspace
          let currentWorkspace = null
          if (workspaces.length > 0) {
            // Try to use last workspace, otherwise use first
            const targetId = userLastWorkspaceId || workspaces[0]._id
            currentWorkspace = workspaces.find(ws => ws._id === targetId) || workspaces[0]
          }
          
          console.log(`✅ Auth Flow: Complete! Total time ${(performance.now() - startTime).toFixed(2)}ms`)
          set({
            workspaces,
            currentWorkspace,
            workspaceLoading: false,
            authLoading: false,
            error: null
          })
          
        } catch (error) {
          // Only log if it's an actual error, not normal flow issues
          if (process.env.NODE_ENV === 'development') {
            loggers.auth.debug('Auth flow error', { error })
          }
          set({
            error: error as Error,
            tokenLoading: false,
            workspaceLoading: false,
            authLoading: false
          })
          throw error
        }
      },
      
      // Clear all auth state
      _clearAuthState: () => {
        // Clear token from manager first
        tokenManager.clearToken()
        
        // Clear refresh token cookie
        clearCookie('refresh-token')
        
        // Clear ALL user-specific localStorage data
        userStorage.clearAll()
        
        // Reset store state
        set({
          firebaseUser: null,
          customToken: null,
          isAuthenticated: false,
          user: null,
          currentWorkspace: null,
          workspaces: [],
          authLoading: false,
          tokenLoading: false,
          workspaceLoading: false,
          error: null
        })
      },
      
      // Sign in with email/password
      signIn: async (email, password) => {
        set({ authLoading: true, error: null })
        
        try {
          const auth = getFirebaseAuth()
          const { user: firebaseUser } = await signInWithEmailAndPassword(auth, email, password)
          
          // The auth state listener will handle the rest
          // Just wait a bit for it to complete
          await new Promise(resolve => setTimeout(resolve, 100))
          
        } catch (error) {
          loggers.auth.error('Sign in failed', { email, error })
          set({ error: error as Error, authLoading: false })
          throw error
        }
      },
      
      // Sign up with email/password
      signUp: async (email, password, displayName) => {
        set({ authLoading: true, error: null })
        
        try {
          const auth = getFirebaseAuth()
          const { user: firebaseUser } = await createUserWithEmailAndPassword(auth, email, password)
          
          if (firebaseUser && displayName) {
            await updateProfile(firebaseUser, { displayName })
          }
          
          // Send verification email if configured
          const config = get().firebaseConfig
          if (config && firebaseUser) {
            await sendEmailVerification(firebaseUser)
          }
          // The auth state listener will handle the rest
          
        } catch (error) {
          loggers.auth.error('Sign up failed', { email, displayName, error })
          set({ error: error as Error, authLoading: false })
          throw error
        }
      },
      
      // Sign out
      signOut: async () => {
        try {
          const auth = getFirebaseAuth()
          await firebaseSignOut(auth)
          
          // Try to call backend logout endpoint
          try {
            await protoboxClient.logout()
          } catch (error) {
            loggers.auth.warn('Backend logout failed', { error })
          }
          
          get()._clearAuthState()
          
        } catch (error) {
          loggers.auth.error('Sign out failed', { error })
          set({ error: error as Error })
          throw error
        }
      },
      
      // Social sign in methods
      signInWithGoogle: async () => {
        set({ authLoading: true, error: null })
        
        try {
          const auth = getFirebaseAuth()
          const provider = new GoogleAuthProvider()
          const { user: firebaseUser } = await signInWithPopup(auth, provider)
          
          // The auth state listener will handle the rest
          await new Promise(resolve => setTimeout(resolve, 100))
          
        } catch (error) {
          loggers.auth.error('Google sign in failed', { error })
          set({ error: error as Error, authLoading: false })
          throw error
        }
      },
      
      signInWithApple: async () => {
        set({ authLoading: true, error: null })
        
        try {
          const auth = getFirebaseAuth()
          const provider = new OAuthProvider('apple.com')
          const { user: firebaseUser } = await signInWithPopup(auth, provider)
          
          // The auth state listener will handle the rest
          await new Promise(resolve => setTimeout(resolve, 100))
          
        } catch (error) {
          loggers.auth.error(' Apple sign in failed:', error)
          set({ error: error as Error, authLoading: false })
          throw error
        }
      },
      
      signInWithFacebook: async () => {
        set({ authLoading: true, error: null })
        
        try {
          const auth = getFirebaseAuth()
          const provider = new FacebookAuthProvider()
          const { user: firebaseUser } = await signInWithPopup(auth, provider)
          
          // The auth state listener will handle the rest
          await new Promise(resolve => setTimeout(resolve, 100))
          
        } catch (error) {
          loggers.auth.error(' Facebook sign in failed:', error)
          set({ error: error as Error, authLoading: false })
          throw error
        }
      },
      
      // Password reset
      resetPassword: async (email) => {
        try {
          const auth = getFirebaseAuth()
          await sendPasswordResetEmail(auth, email)
        } catch (error) {
          set({ error: error as Error })
          throw error
        }
      },
      
      // Update password
      updatePassword: async (newPassword) => {
        const { firebaseUser } = get()
        if (!firebaseUser) throw new Error('No user signed in')
        
        try {
          await updatePassword(firebaseUser, newPassword)
        } catch (error) {
          set({ error: error as Error })
          throw error
        }
      },
      
      // Update profile
      updateProfile: async (displayName) => {
        const { firebaseUser } = get()
        if (!firebaseUser) throw new Error('No user signed in')
        
        try {
          await updateProfile(firebaseUser, { displayName })
          set({ user: { ...get().user, displayName } as AuthUser })
        } catch (error) {
          set({ error: error as Error })
          throw error
        }
      },
      
      // Send email verification
      sendEmailVerification: async () => {
        const { firebaseUser } = get()
        if (!firebaseUser) throw new Error('No user signed in')
        
        try {
          await sendEmailVerification(firebaseUser)
        } catch (error) {
          set({ error: error as Error })
          throw error
        }
      },
      
      // Workspace management
      loadWorkspaces: async () => {
        set({ workspaceLoading: true, error: null })
        
        try {
          const response = await protoboxClient.getWorkspaces()
          const workspaces = response.data?.workspaces || []
          
          set({
            workspaces,
            workspaceLoading: false
          })
          
          return workspaces
        } catch (error) {
          loggers.auth.error(' Load workspaces failed:', error)
          set({ error: error as Error, workspaceLoading: false })
          throw error
        }
      },
      
      selectWorkspace: async (workspaceId) => {
        const { workspaces } = get()
        const workspace = workspaces.find(ws => ws._id === workspaceId || ws.id === workspaceId)
        
        if (!workspace) {
          throw new Error('Workspace not found')
        }
        
        set({ currentWorkspace: workspace })
        
        // Update last workspace on backend
        try {
          await protoboxClient.updateLastWorkspace(workspaceId)
        } catch (error) {
          loggers.auth.warn(' Failed to update last workspace:', error)
        }
      },
      
      createWorkspace: async (name) => {
        set({ workspaceLoading: true, error: null })
        
        try {
          const response = await protoboxClient.createWorkspace({ name })
          const newWorkspace = response.data?.workspace || response.data
          
          // Add to workspaces list and select it
          const workspaces = [...get().workspaces, newWorkspace]
          set({
            workspaces,
            currentWorkspace: newWorkspace,
            workspaceLoading: false
          })
          
          return newWorkspace
        } catch (error) {
          loggers.auth.error(' Create workspace failed:', error)
          set({ error: error as Error, workspaceLoading: false })
          throw error
        }
      },
      
      refreshWorkspaces: async () => {
        await get().loadWorkspaces()
        
        // Re-select current workspace if it still exists
        const { currentWorkspace, workspaces } = get()
        // A user whose first workspace was created during onboarding has no current
        // workspace yet, so the dashboard guard would show "unable to select one".
        if (!currentWorkspace && workspaces.length > 0) {
          set({ currentWorkspace: workspaces[0] })
        } else if (currentWorkspace && workspaces.length > 0) {
          const updatedWorkspace = workspaces.find(ws => ws._id === currentWorkspace._id)
          if (updatedWorkspace) {
            // Update the current workspace with fresh data
            set({ currentWorkspace: updatedWorkspace })
          } else if (workspaces.length > 0) {
            // If current workspace doesn't exist anymore, select the first one
            set({ currentWorkspace: workspaces[0] })
          }
        }
      }
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist non-sensitive UI preferences
        // Don't persist tokens, user data, or workspace data
        // Those should be fetched fresh on each session
      })
    }
  )
)