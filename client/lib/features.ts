// Feature flags configuration
export interface FeatureFlags {
  promptManagement: boolean
  memories: boolean
}

// Default feature flags - can be overridden via environment variables
const defaultFlags: FeatureFlags = {
  promptManagement: process.env.NEXT_PUBLIC_FEATURE_PROMPTS === 'true' || false,
  memories: false, // Memories feature disabled
}

// Feature flag manager
class FeatureFlagManager {
  private flags: FeatureFlags

  constructor() {
    this.flags = { ...defaultFlags }
  }

  isEnabled(feature: keyof FeatureFlags): boolean {
    return this.flags[feature]
  }

  setFlag(feature: keyof FeatureFlags, enabled: boolean) {
    this.flags[feature] = enabled
  }

  getAllFlags(): FeatureFlags {
    return { ...this.flags }
  }
}

export const featureFlags = new FeatureFlagManager()

// Hook for using feature flags in React components
import { useState, useEffect } from 'react'

export function useFeatureFlag(feature: keyof FeatureFlags): boolean {
  const [enabled, setEnabled] = useState(() => featureFlags.isEnabled(feature))

  useEffect(() => {
    // Re-check the flag value on mount in case it changed
    setEnabled(featureFlags.isEnabled(feature))
  }, [feature])

  return enabled
}