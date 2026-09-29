import { useCallback, useEffect, useState } from 'react'
import { analyticsAPI, type DashboardStats, type ExecutionMetrics, type RecentActivity } from '@/lib/api/analytics'

// Cache configuration
const CACHE_TTL = 60 * 1000 // 1 minute
const STALE_TIME = 30 * 1000 // 30 seconds

interface CacheEntry<T> {
  data: T
  timestamp: number
}

class AnalyticsCache {
  private cache: Map<string, CacheEntry<any>> = new Map()

  get<T>(key: string): T | null {
    const entry = this.cache.get(key)
    if (!entry) return null
    
    const age = Date.now() - entry.timestamp
    if (age > CACHE_TTL) {
      this.cache.delete(key)
      return null
    }
    
    return entry.data
  }

  set<T>(key: string, data: T): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    })
  }

  isStale(key: string): boolean {
    const entry = this.cache.get(key)
    if (!entry) return true
    
    const age = Date.now() - entry.timestamp
    return age > STALE_TIME
  }

  clear(): void {
    this.cache.clear()
  }
}

const analyticsCache = new AnalyticsCache()

// Individual metric hooks with caching
export function useDashboardStats(workspaceId: string, timeRange: string = '7d') {
  const [data, setData] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const cacheKey = `stats-${timeRange}-${workspaceId}`

  const fetchData = useCallback(async (forceRefresh = false) => {
    try {
      // Check cache first
      if (!forceRefresh) {
        const cached = analyticsCache.get<DashboardStats>(cacheKey)
        if (cached) {
          setData(cached)
          setLoading(false)
          
          // Fetch in background if stale
          if (analyticsCache.isStale(cacheKey)) {
            analyticsAPI.getDashboardStats(workspaceId, timeRange)
              .then(freshData => {
                analyticsCache.set(cacheKey, freshData)
                setData(freshData)
              })
          }
          return
        }
      }

      setLoading(true)
      const freshData = await analyticsAPI.getDashboardStats(workspaceId, timeRange)
      analyticsCache.set(cacheKey, freshData)
      setData(freshData)
      setError(null)
    } catch (err) {
      setError(err as Error)
      // Use cached data if available on error
      const cached = analyticsCache.get<DashboardStats>(cacheKey)
      if (cached) {
        setData(cached)
      }
    } finally {
      setLoading(false)
    }
  }, [timeRange, workspaceId, cacheKey])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { data, loading, error, refetch: () => fetchData(true) }
}

export function useExecutionMetrics(workspaceId: string, timeRange: string = '7d') {
  const [data, setData] = useState<ExecutionMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const cacheKey = `metrics-${timeRange}-${workspaceId}`

  const fetchData = useCallback(async (forceRefresh = false) => {
    try {
      // Check cache first
      if (!forceRefresh) {
        const cached = analyticsCache.get<ExecutionMetrics>(cacheKey)
        if (cached) {
          setData(cached)
          setLoading(false)
          
          // Fetch in background if stale
          if (analyticsCache.isStale(cacheKey)) {
            analyticsAPI.getExecutionMetrics(workspaceId, timeRange)
              .then(freshData => {
                analyticsCache.set(cacheKey, freshData)
                setData(freshData)
              })
          }
          return
        }
      }

      setLoading(true)
      const freshData = await analyticsAPI.getExecutionMetrics(workspaceId, timeRange)
      analyticsCache.set(cacheKey, freshData)
      setData(freshData)
      setError(null)
    } catch (err) {
      setError(err as Error)
      // Use cached data if available on error
      const cached = analyticsCache.get<ExecutionMetrics>(cacheKey)
      if (cached) {
        setData(cached)
      }
    } finally {
      setLoading(false)
    }
  }, [timeRange, workspaceId, cacheKey])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { data, loading, error, refetch: () => fetchData(true) }
}

export function useRecentActivity(workspaceId: string, limit: number = 10) {
  const [data, setData] = useState<RecentActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const cacheKey = `activity-${limit}-${workspaceId}`

  const fetchData = useCallback(async (forceRefresh = false) => {
    try {
      // Check cache first
      if (!forceRefresh) {
        const cached = analyticsCache.get<RecentActivity[]>(cacheKey)
        if (cached) {
          setData(cached)
          setLoading(false)
          
          // Fetch in background if stale (recent activity should update more frequently)
          if (analyticsCache.isStale(cacheKey)) {
            analyticsAPI.getRecentActivity(workspaceId, limit)
              .then(freshData => {
                analyticsCache.set(cacheKey, freshData)
                setData(freshData)
              })
          }
          return
        }
      }

      setLoading(true)
      const freshData = await analyticsAPI.getRecentActivity(workspaceId, limit)
      analyticsCache.set(cacheKey, freshData)
      setData(freshData)
      setError(null)
    } catch (err) {
      setError(err as Error)
      // Use cached data if available on error
      const cached = analyticsCache.get<RecentActivity[]>(cacheKey)
      if (cached) {
        setData(cached)
      }
    } finally {
      setLoading(false)
    }
  }, [limit, workspaceId, cacheKey])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return { data, loading, error, refetch: () => fetchData(true) }
}

// Combined hook for dashboard that fetches all data in parallel
export function useDashboardData(workspaceId: string, timeRange: string = '7d') {
  const stats = useDashboardStats(workspaceId, timeRange)
  const metrics = useExecutionMetrics(workspaceId, timeRange)
  const activity = useRecentActivity(workspaceId, 10)

  const loading = stats.loading || metrics.loading || activity.loading
  const hasError = !!(stats.error || metrics.error || activity.error)

  const refetchAll = useCallback(() => {
    stats.refetch()
    metrics.refetch()
    activity.refetch()
  }, [stats, metrics, activity])

  return {
    stats: stats.data,
    metrics: metrics.data,
    activity: activity.data,
    loading,
    hasError,
    errors: {
      stats: stats.error,
      metrics: metrics.error,
      activity: activity.error
    },
    refetch: refetchAll
  }
}

// Utility to clear all caches
export function clearAnalyticsCache() {
  analyticsCache.clear()
}