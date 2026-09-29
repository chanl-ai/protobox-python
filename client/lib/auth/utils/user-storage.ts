/**
 * Centralized storage manager for user-specific data
 * This ensures all user data is properly cleared on logout
 */

interface UserStorageData {
  lastWorkspaceId?: string
  workspacePreferences?: Record<string, any>
  uiPreferences?: {
    theme?: 'light' | 'dark'
    sidebarCollapsed?: boolean
    dashboardLayout?: string
  }
  // Add more user-specific data here as needed
}

class UserStorageManager {
  private readonly STORAGE_KEY = 'protobox-user-data'
  
  /**
   * Get all user data from localStorage
   */
  getData(): UserStorageData {
    if (typeof window === 'undefined') return {}
    
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY)
      return stored ? JSON.parse(stored) : {}
    } catch (error) {
      console.error('Failed to parse user storage data:', error)
      return {}
    }
  }
  
  /**
   * Set a specific field in user data
   */
  setField<K extends keyof UserStorageData>(
    field: K, 
    value: UserStorageData[K]
  ): void {
    if (typeof window === 'undefined') return
    
    const data = this.getData()
    data[field] = value
    
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data))
    } catch (error) {
      console.error('Failed to save user storage data:', error)
    }
  }
  
  /**
   * Get a specific field from user data
   */
  getField<K extends keyof UserStorageData>(
    field: K
  ): UserStorageData[K] | undefined {
    const data = this.getData()
    return data[field]
  }
  
  /**
   * Clear all user data from localStorage
   * Called on logout
   */
  clearAll(): void {
    if (typeof window === 'undefined') return
    
    // Clear our centralized storage
    localStorage.removeItem(this.STORAGE_KEY)
    
    // Clear any legacy individual items
    const legacyKeys = [
      'lastWorkspaceId',
      'auth-token',
      'refresh-token',
      // Add any other legacy keys here
    ]
    
    legacyKeys.forEach(key => {
      localStorage.removeItem(key)
    })
    
    // Clear Zustand persisted stores
    const zustandKeys = Object.keys(localStorage).filter(key => 
      key.includes('auth-storage') || 
      key.includes('workspace-storage')
    )
    
    zustandKeys.forEach(key => {
      localStorage.removeItem(key)
    })
  }
  
  /**
   * Migrate legacy localStorage items to centralized storage
   */
  migrateLegacyData(): void {
    if (typeof window === 'undefined') return
    
    const data = this.getData()
    
    // Migrate lastWorkspaceId if it exists
    const lastWorkspaceId = localStorage.getItem('lastWorkspaceId')
    if (lastWorkspaceId && !data.lastWorkspaceId) {
      data.lastWorkspaceId = lastWorkspaceId
      localStorage.removeItem('lastWorkspaceId')
    }
    
    // Save migrated data
    if (Object.keys(data).length > 0) {
      try {
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data))
      } catch (error) {
        console.error('Failed to migrate user storage data:', error)
      }
    }
  }
}

// Export singleton instance
export const userStorage = new UserStorageManager()

// Auto-migrate on load
if (typeof window !== 'undefined') {
  userStorage.migrateLegacyData()
}