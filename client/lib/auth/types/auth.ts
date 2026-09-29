import { User as FirebaseUser } from 'firebase/auth'

export interface AuthUser extends FirebaseUser {
  customToken?: string
  workspaceId?: string
}

export interface AuthState {
  user: AuthUser | null
  loading: boolean
  error: Error | null
  initialized: boolean
}

export interface AuthError {
  code: string
  message: string
  originalError?: any
}

export interface BackendIntegration {
  exchangeToken: (firebaseToken: string) => Promise<any>
  validateToken?: (token: string) => Promise<any>
  createApiKey?: (userId: string) => Promise<any>
  fetchWorkspaces?: () => Promise<any>
  endpoints?: {
    logout?: string
  }
}

export interface AuthContextValue extends AuthState {
  signIn: (email: string, password: string) => Promise<AuthUser | null>
  signUp: (email: string, password: string, displayName?: string) => Promise<AuthUser | null>
  signOut: () => Promise<void>
  signInWithGoogle: () => Promise<AuthUser | null>
  signInWithApple: () => Promise<AuthUser | null>
  signInWithFacebook: () => Promise<AuthUser | null>
  resetPassword: (email: string) => Promise<void>
  updatePassword: (newPassword: string) => Promise<void>
  updateProfile: (displayName: string) => Promise<void>
  sendEmailVerification: () => Promise<void>
}