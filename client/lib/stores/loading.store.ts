import { create } from 'zustand'

interface RequestInfo {
  id: string
  message?: string
  startTime: number
  retryCount: number
  endpoint?: string
  critical?: boolean // Critical requests get longer timeouts
}

interface LoadingState {
  // State
  activeRequests: Map<string, RequestInfo>
  isGlobalLoading: boolean
  coldStartDetected: boolean
  currentMessage: string
  error: { message: string; canRetry: boolean } | null
  showDialog: boolean
  
  // Metrics
  firstRequestTime: number | null
  averageResponseTime: number
  
  // Actions
  startRequest: (id: string, message?: string, endpoint?: string, critical?: boolean) => void
  endRequest: (id: string, success?: boolean) => void
  setError: (message: string, canRetry?: boolean) => void
  clearError: () => void
  retry: () => void
  cancel: () => void
  setMessage: (message: string) => void
}

// Helper to generate progressive messages based on duration
const getProgressiveMessage = (duration: number, isFirstRequest: boolean, message?: string): string => {
  if (message) return message
  
  if (duration < 3000) {
    return 'Fetching your data...'
  } else if (duration < 10000) {
    return 'Still working on your request...'
  } else if (duration < 20000) {
    return isFirstRequest ? 'Server is waking up from idle state...' : 'Processing complex operation...'
  } else if (duration < 30000) {
    return 'This is taking longer than expected. Almost done...'
  } else {
    return 'The operation is taking unusually long. You may want to retry.'
  }
}

export const useLoadingStore = create<LoadingState>((set, get) => ({
  // Initial state
  activeRequests: new Map(),
  isGlobalLoading: false,
  coldStartDetected: false,
  currentMessage: '',
  error: null,
  showDialog: false,
  firstRequestTime: null,
  averageResponseTime: 5000, // Start with 5s estimate
  
  // Start a new request
  startRequest: (id: string, message?: string, endpoint?: string, critical = false) => {
    const state = get()
    const now = Date.now()
    
    // Track first request time for cold start detection
    if (!state.firstRequestTime) {
      set({ firstRequestTime: now })
    }
    
    // Create request info
    const requestInfo: RequestInfo = {
      id,
      message,
      startTime: now,
      retryCount: 0,
      endpoint,
      critical,
    }
    
    // Update state
    const newRequests = new Map(state.activeRequests)
    newRequests.set(id, requestInfo)
    
    // Don't show dialog immediately - let the delay timer handle it
    set({
      activeRequests: newRequests,
      isGlobalLoading: newRequests.size > 0,
      showDialog: false, // Start with dialog hidden
      currentMessage: message || 'Fetching your data...',
      error: null, // Clear any previous errors
    })
    
    // Only show dialog for critical operations or errors
    // Normal page loads will just use the top loading bar
    if (critical) {
      // Show immediately for critical requests only
      set({ showDialog: true })
    }
    // No dialog timer needed anymore - we're using the top bar for regular loads
    
    // Set up progressive message updates
    const messageInterval = setInterval(() => {
      const currentState = get()
      const request = currentState.activeRequests.get(id)
      
      if (!request) {
        clearInterval(messageInterval)
        return
      }
      
      const duration = Date.now() - request.startTime
      const isFirst = currentState.firstRequestTime === request.startTime
      
      // Detect cold start (first request taking > 3s)
      if (isFirst && duration > 3000 && !currentState.coldStartDetected) {
        set({ coldStartDetected: true })
        // Only show dialog for cold start if it takes really long (>10s)
        if (duration > 10000) {
          set({ showDialog: true })
        }
      }
      
      // Update message
      const newMessage = getProgressiveMessage(duration, isFirst, request.message)
      if (newMessage !== currentState.currentMessage) {
        set({ currentMessage: newMessage })
      }
      
      // Show timeout warning after 30s
      if (duration > 30000 && !currentState.error) {
        set({ 
          error: { 
            message: 'Request timeout. The server might be experiencing issues.', 
            canRetry: true 
          } 
        })
      }
    }, 1000)
    
    // Store interval ID for cleanup
    ;(window as any)[`loading_interval_${id}`] = messageInterval
  },
  
  // End a request
  endRequest: (id: string, success = true) => {
    const state = get()
    const request = state.activeRequests.get(id)
    
    if (!request) return
    
    // Clear interval
    const intervalId = (window as any)[`loading_interval_${id}`]
    if (intervalId) {
      clearInterval(intervalId)
      delete (window as any)[`loading_interval_${id}`]
    }
    
    // Update average response time if successful
    if (success) {
      const duration = Date.now() - request.startTime
      const newAverage = (state.averageResponseTime * 0.7) + (duration * 0.3) // Weighted average
      set({ averageResponseTime: Math.round(newAverage) })
    }
    
    // Remove request
    const newRequests = new Map(state.activeRequests)
    newRequests.delete(id)
    
    // Update state - don't show dialog for normal request completions
    set({
      activeRequests: newRequests,
      isGlobalLoading: newRequests.size > 0,
      showDialog: false, // Don't show dialog when requests complete
      currentMessage: newRequests.size > 0 ? 'Fetching your data...' : '',
      // Reset cold start detection after successful requests
      coldStartDetected: success ? false : state.coldStartDetected,
    })
  },
  
  // Set error state
  setError: (message: string, canRetry = true) => {
    set({ 
      error: { message, canRetry },
      showDialog: true,
    })
  },
  
  // Clear error
  clearError: () => {
    set({ error: null })
  },
  
  // Retry failed requests
  retry: () => {
    const state = get()
    
    // Clear error
    set({ error: null })
    
    // Trigger retry logic (this will be handled by the API client)
    window.dispatchEvent(new CustomEvent('api-retry'))
  },
  
  // Cancel all requests
  cancel: () => {
    const state = get()
    
    // Clear all intervals and timers
    state.activeRequests.forEach((_, id) => {
      const intervalId = (window as any)[`loading_interval_${id}`]
      if (intervalId) {
        clearInterval(intervalId)
        delete (window as any)[`loading_interval_${id}`]
      }
    })
    
    // Reset state
    set({
      activeRequests: new Map(),
      isGlobalLoading: false,
      showDialog: false,
      currentMessage: '',
      error: null,
    })
    
    // Trigger cancel event
    window.dispatchEvent(new CustomEvent('api-cancel'))
  },
  
  // Set custom message
  setMessage: (message: string) => {
    set({ currentMessage: message })
  },
}))