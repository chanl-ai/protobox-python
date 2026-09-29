import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { BillingManager, BillingInfo, Subscription, UsageMetrics } from '../managers/billing-manager'
import { useAuthStore } from '../stores/auth.store'

export interface BillingContextType {
  billingInfo: BillingInfo | null
  loading: boolean
  error: string | null
  updateSubscription: (plan: 'free' | 'pro' | 'enterprise') => Promise<Subscription>
  cancelSubscription: () => Promise<void>
  updateUsage: (usage: Partial<UsageMetrics>) => Promise<void>
  refreshBillingInfo: () => Promise<void>
}

export interface BillingConfig {
  provider?: 'stripe' | 'paddle' | 'custom'
  plans?: {
    [key: string]: {
      name: string
      price: number
      features: string[]
      limits: {
        api_requests: number
        storage_mb: number
        team_members: number
      }
    }
  }
  features?: {
    [key: string]: string[]
  }
  onSubscriptionChange?: (subscription: Subscription) => void
}

const BillingContext = createContext<BillingContextType | undefined>(undefined)

export function createBillingProvider(config: BillingConfig = {}) {
  return function BillingProvider({ children }: { children: ReactNode }) {
    const [billingInfo, setBillingInfo] = useState<BillingInfo | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    
    const { currentWorkspace } = useAuthStore()
    const billingManager = new BillingManager()
    
    useEffect(() => {
      if (currentWorkspace) {
        loadBillingInfo()
      } else {
        setBillingInfo(null)
      }
    }, [currentWorkspace?._id])
    
    const loadBillingInfo = async () => {
      if (!currentWorkspace) return
      
      try {
        setLoading(true)
        setError(null)
        const info = await billingManager.getBillingInfo(currentWorkspace._id.toString())
        setBillingInfo(info)
      } catch (err) {
        setError('Failed to load billing information')
      } finally {
        setLoading(false)
      }
    }
    
    const updateSubscription = async (plan: 'free' | 'pro' | 'enterprise'): Promise<Subscription> => {
      if (!currentWorkspace) {
        throw new Error('No workspace selected')
      }
      
      try {
        setLoading(true)
        setError(null)
        
        const subscription = await billingManager.createSubscription(
          currentWorkspace._id.toString(),
          plan
        )
        
        // Refresh billing info
        await loadBillingInfo()
        
        // Call custom callback if provided
        if (config.onSubscriptionChange) {
          config.onSubscriptionChange(subscription)
        }
        
        return subscription
      } catch (err) {
        setError('Failed to update subscription')
        throw err
      } finally {
        setLoading(false)
      }
    }
    
    const cancelSubscription = async () => {
      if (!currentWorkspace) {
        throw new Error('No workspace selected')
      }
      
      try {
        setLoading(true)
        setError(null)
        
        await billingManager.cancelSubscription(currentWorkspace._id.toString())
        
        // Refresh billing info
        await loadBillingInfo()
      } catch (err) {
        setError('Failed to cancel subscription')
        throw err
      } finally {
        setLoading(false)
      }
    }
    
    const updateUsage = async (usage: Partial<UsageMetrics>) => {
      if (!currentWorkspace) return
      
      try {
        await billingManager.updateUsage(currentWorkspace._id.toString(), usage)
        // Optionally refresh billing info to get updated usage
        // await loadBillingInfo()
      } catch (err) {
      }
    }
    
    const value: BillingContextType = {
      billingInfo,
      loading,
      error,
      updateSubscription,
      cancelSubscription,
      updateUsage,
      refreshBillingInfo: loadBillingInfo
    }
    
    return (
      <BillingContext.Provider value={value}>
        {children}
      </BillingContext.Provider>
    )
  }
}

export function useBilling() {
  const context = useContext(BillingContext)
  if (context === undefined) {
    throw new Error('useBilling must be used within a BillingProvider')
  }
  return context
}

// Export the context for custom providers
export { BillingContext }