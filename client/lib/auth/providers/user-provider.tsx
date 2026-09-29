import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User, UserManager, UserPreferences, CreateUserData } from '../managers/user-manager'
import { useAuth } from '../hooks/useAuth'

export interface UserContextType {
  userData: User | null
  loading: boolean
  error: string | null
  updatePreferences: (preferences: Partial<UserPreferences>) => Promise<User | null>
  updateUser: (updates: Partial<User>) => Promise<User | null>
  refreshUser: () => Promise<void>
}

export interface UserConfig {
  defaultPreferences?: {
    theme?: 'light' | 'dark'
    language?: string
    timezone?: string
    emailNotifications?: boolean
  }
  customFields?: string[]
  onUserUpdate?: (user: User) => void
}

const UserContext = createContext<UserContextType | undefined>(undefined)

export function createUserProvider(config: UserConfig = {}) {
  return function UserProvider({ children }: { children: ReactNode }) {
    const [userData, setUserData] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    
    const { user: firebaseUser } = useAuth()
    const userManager = new UserManager()
    
    useEffect(() => {
      if (firebaseUser) {
        loadOrCreateUser()
      } else {
        setUserData(null)
        setLoading(false)
      }
    }, [firebaseUser?.uid])
    
    const loadOrCreateUser = async () => {
      if (!firebaseUser) return
      
      try {
        setLoading(true)
        setError(null)
        
        // Try to get existing user by Firebase UID
        let user = await userManager.getUserByFirebaseUid(firebaseUser.uid)
        
        if (!user) {
          // Create new user if doesn't exist
          const createData: CreateUserData = {
            email: firebaseUser.email || '',
            displayName: firebaseUser.displayName || firebaseUser.email || 'User',
            firebaseUid: firebaseUser.uid
          }
          
          user = await userManager.createUser(createData)
        }
        
        setUserData(user)
      } catch (err) {
        setError('Failed to load user data')
      } finally {
        setLoading(false)
      }
    }
    
    const updatePreferences = async (preferences: Partial<UserPreferences>): Promise<User | null> => {
      if (!userData) {
        throw new Error('No user data available')
      }
      
      try {
        setError(null)
        
        const mergedPreferences = {
          ...userData.preferences,
          ...config.defaultPreferences,
          ...preferences
        }
        
        const updated = await userManager.updatePreferences(
          userData._id.toString(),
          mergedPreferences
        )
        
        if (updated) {
          setUserData(updated)
          
          // Call custom callback if provided
          if (config.onUserUpdate) {
            config.onUserUpdate(updated)
          }
        }
        
        return updated
      } catch (err) {
        setError('Failed to update preferences')
        throw err
      }
    }
    
    const updateUser = async (updates: Partial<User>): Promise<User | null> => {
      if (!userData) {
        throw new Error('No user data available')
      }
      
      try {
        setError(null)
        
        const updated = await userManager.updateUser(
          userData._id.toString(),
          updates
        )
        
        if (updated) {
          setUserData(updated)
          
          // Call custom callback if provided
          if (config.onUserUpdate) {
            config.onUserUpdate(updated)
          }
        }
        
        return updated
      } catch (err) {
        setError('Failed to update user')
        throw err
      }
    }
    
    const value: UserContextType = {
      userData,
      loading,
      error,
      updatePreferences,
      updateUser,
      refreshUser: loadOrCreateUser
    }
    
    return (
      <UserContext.Provider value={value}>
        {children}
      </UserContext.Provider>
    )
  }
}

export function useUser() {
  const context = useContext(UserContext)
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider')
  }
  return context
}

// Export the context for custom providers
export { UserContext }