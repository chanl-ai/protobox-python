"use client"

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
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
  sendEmailVerification as firebaseSendEmailVerification,
  updatePassword as firebaseUpdatePassword,
  updateProfile as firebaseUpdateProfile
} from 'firebase/auth'
import { 
  AuthContextValue, 
  AuthState, 
  BackendIntegration,
  FirebaseAuthConfig 
} from '../types'
import { getFirebaseAuth } from '../utils/firebase'

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

interface AuthProviderProps {
  children: React.ReactNode
  config: FirebaseAuthConfig
  backendIntegration?: BackendIntegration
  onAuthStateChange?: (user: User | null) => void
  testMode?: {
    enabled?: boolean | (() => boolean)
    autoLogin?: boolean
    testUser?: {
      uid: string
      email: string
      displayName?: string
      emailVerified?: boolean
    }
    testToken?: string
  }
}

export function AuthProvider({ 
  children, 
  config, 
  backendIntegration,
  onAuthStateChange,
  testMode 
}: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    error: null,
    initialized: false
  })

  const auth = getFirebaseAuth()
  
  // No need for test mode in auth context - Firebase works normally

  // Handle token exchange if backend integration is provided
  const handleTokenExchange = useCallback(async (firebaseUser: User) => {
    if (!backendIntegration) {
      console.log('[AuthContext] No backend integration provided')
      return
    }

    console.log('[AuthContext] Starting token exchange for user:', firebaseUser.email)
    try {
      const idToken = await firebaseUser.getIdToken()
      const result = await backendIntegration.exchangeToken(idToken)
      
      console.log('[AuthContext] Token exchange result:', { 
        hasToken: !!result?.token, 
        hasUser: !!result?.user,
        workspaceId: result?.user?.workspace_id 
      })
      
      // Store the tokens if exchange was successful
      if (result?.token) {
        const { storeToken, storeRefreshToken } = await import('../utils/storage')
        storeToken(result.token)
        
        // Store refresh token if available
        if (result.refreshToken) {
          storeRefreshToken(result.refreshToken)
        }
        
        // Update user with custom token
        const userWithToken = Object.assign({}, firebaseUser, {
          customToken: result.token,
          workspaceId: result.user?.workspace_id || undefined
        })
        
        console.log('[AuthContext] User updated with token:', {
          email: userWithToken.email,
          hasToken: !!userWithToken.customToken,
          hasRefreshToken: !!result.refreshToken,
          workspaceId: userWithToken.workspaceId
        })
        
        setState(prev => ({ 
          ...prev, 
          user: userWithToken,
          loading: false,
          initialized: true
        }))
        return result
      }
    } catch (error) {
      console.error('[AuthContext] Token exchange failed:', error)
      setState(prev => ({ ...prev, error: error as Error }))
    }
  }, [backendIntegration])

  useEffect(() => {
    console.log('[AuthContext] Setting up auth state listener')
    // Normal Firebase auth flow
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      console.log('[AuthContext] Auth state changed:', {
        hasUser: !!firebaseUser,
        email: firebaseUser?.email,
        uid: firebaseUser?.uid
      })
      
      if (firebaseUser) {
        // Check for stored token
        const { getToken } = await import('../utils/storage')
        const storedToken = getToken()
        console.log('[AuthContext] Stored token exists:', !!storedToken)
        
        // Set user immediately to prevent auth loops
        const initialUser = Object.assign({}, firebaseUser, {
          customToken: storedToken || undefined,
          workspaceId: undefined
        })
        setState(prev => ({ ...prev, user: initialUser }))
        
        // Handle token exchange if needed
        if (backendIntegration && !storedToken) {
          console.log('[AuthContext] No stored token, performing token exchange')
          await handleTokenExchange(firebaseUser)
        } else {
          // If no backend integration or token already exists, just mark as loaded
          console.log('[AuthContext] Using stored token or no backend integration')
          setState(prev => ({
            ...prev,
            loading: false,
            initialized: true
          }))
        }
      } else {
        console.log('[AuthContext] No user, clearing state')
        setState({
          user: null,
          loading: false,
          error: null,
          initialized: true
        })
      }

      // Call the optional callback
      onAuthStateChange?.(firebaseUser)
    })

    return unsubscribe
  }, [auth, backendIntegration, handleTokenExchange, onAuthStateChange])

  const signIn = async (email: string, password: string) => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))
      const { user } = await signInWithEmailAndPassword(auth, email, password)
      
      if (user && backendIntegration) {
        const result = await handleTokenExchange(user)
        // Return the user with customToken
        return state.user
      }
      
      return user
    } catch (error) {
      setState(prev => ({ ...prev, error: error as Error, loading: false }))
      throw error
    }
  }

  const signUp = async (email: string, password: string, displayName?: string) => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))
      const { user } = await createUserWithEmailAndPassword(auth, email, password)
      
      if (user) {
        // Update display name if provided
        if (displayName) {
          await firebaseUpdateProfile(user, { displayName })
        }
        
        // Send verification email
        if (config.ui?.showEmailVerification !== false) {
          await firebaseSendEmailVerification(user)
        }
        
        if (backendIntegration) {
          await handleTokenExchange(user)
          return state.user
        }
        
        return user
      }
      
      return null
    } catch (error) {
      setState(prev => ({ ...prev, error: error as Error, loading: false }))
      throw error
    }
  }

  const signOut = async () => {
    try {
      await firebaseSignOut(auth)
      
      // Clear the auth cookie via logout endpoint if available
      if (backendIntegration?.endpoints?.logout) {
        try {
          await fetch(backendIntegration.endpoints.logout, {
            method: 'POST',
            credentials: 'include'
          })
        } catch (error) {
          // Log but don't throw - cookie clearing is not critical
          console.warn('Failed to clear auth cookie:', error)
        }
      }
      
      setState(prev => ({ ...prev, user: null }))
    } catch (error) {
      setState(prev => ({ ...prev, error: error as Error }))
      throw error
    }
  }

  const signInWithGoogle = async () => {
    console.log('[AuthContext] Starting Google sign in')
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))
      const provider = new GoogleAuthProvider()
      console.log('[AuthContext] Opening Google popup')
      const { user } = await signInWithPopup(auth, provider)
      console.log('[AuthContext] Google popup completed, user:', user?.email)
      
      if (user && backendIntegration) {
        console.log('[AuthContext] User authenticated, starting token exchange')
        await handleTokenExchange(user)
        console.log('[AuthContext] Token exchange completed, returning user')
        return state.user
      }
      
      console.log('[AuthContext] No backend integration, returning Firebase user')
      return user
    } catch (error) {
      console.error('[AuthContext] Google sign in error:', error)
      setState(prev => ({ ...prev, error: error as Error, loading: false }))
      throw error
    }
  }

  const signInWithApple = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))
      const provider = new OAuthProvider('apple.com')
      const { user } = await signInWithPopup(auth, provider)
      
      if (user && backendIntegration) {
        await handleTokenExchange(user)
        return state.user
      }
      
      return user
    } catch (error) {
      setState(prev => ({ ...prev, error: error as Error, loading: false }))
      throw error
    }
  }

  const signInWithFacebook = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }))
      const provider = new FacebookAuthProvider()
      const { user } = await signInWithPopup(auth, provider)
      
      if (user && backendIntegration) {
        await handleTokenExchange(user)
        return state.user
      }
      
      return user
    } catch (error) {
      setState(prev => ({ ...prev, error: error as Error, loading: false }))
      throw error
    }
  }

  const resetPassword = async (email: string) => {
    try {
      await sendPasswordResetEmail(auth, email)
    } catch (error) {
      setState(prev => ({ ...prev, error: error as Error }))
      throw error
    }
  }

  const updatePassword = async (newPassword: string) => {
    if (!state.user) throw new Error('No user logged in')
    
    try {
      await firebaseUpdatePassword(state.user, newPassword)
    } catch (error) {
      setState(prev => ({ ...prev, error: error as Error }))
      throw error
    }
  }

  const updateProfile = async (displayName: string) => {
    if (!state.user) throw new Error('No user logged in')
    
    try {
      await firebaseUpdateProfile(state.user, { displayName })
    } catch (error) {
      setState(prev => ({ ...prev, error: error as Error }))
      throw error
    }
  }

  const sendEmailVerification = async () => {
    if (!state.user) throw new Error('No user logged in')
    
    try {
      await firebaseSendEmailVerification(state.user)
    } catch (error) {
      setState(prev => ({ ...prev, error: error as Error }))
      throw error
    }
  }

  const value: AuthContextValue = {
    ...state,
    signIn,
    signUp,
    signOut,
    signInWithGoogle,
    signInWithApple,
    signInWithFacebook,
    resetPassword,
    updatePassword,
    updateProfile,
    sendEmailVerification
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}