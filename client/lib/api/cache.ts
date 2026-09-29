/**
 * Simple in-memory cache for API responses
 * Reduces repeated API calls during workspace loading/switching
 */

interface CacheEntry<T> {
  data: T
  timestamp: number
  ttl: number
}

class ApiCache {
  private cache = new Map<string, CacheEntry<any>>()

  get<T>(key: string): T | null {
    const entry = this.cache.get(key)
    if (!entry) return null

    const now = Date.now()
    if (now - entry.timestamp > entry.ttl) {
      this.cache.delete(key)
      return null
    }

    return entry.data
  }

  set<T>(key: string, data: T, ttlMs: number = 30000): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl: ttlMs
    })
  }

  delete(key: string): void {
    this.cache.delete(key)
  }

  clear(): void {
    this.cache.clear()
  }

  // Clear expired entries
  cleanup(): void {
    const now = Date.now()
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        this.cache.delete(key)
      }
    }
  }
}

export const apiCache = new ApiCache()

// Cleanup expired entries every 5 minutes
if (typeof window !== 'undefined') {
  setInterval(() => apiCache.cleanup(), 5 * 60 * 1000)
}

/**
 * Cache wrapper for API calls
 */
export async function withCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttlMs: number = 30000
): Promise<T> {
  // Try cache first
  const cached = apiCache.get<T>(key)
  if (cached) {
    return cached
  }

  // Fetch and cache
  const data = await fetcher()
  apiCache.set(key, data, ttlMs)
  return data
}

/**
 * Cache keys for different API endpoints
 */
export const cacheKeys = {
  workspaces: (userId?: string) => `workspaces:${userId || 'current'}`,
  workspace: (workspaceId: string) => `workspace:${workspaceId}`,
  workspaceStats: (workspaceId: string) => `workspace-stats:${workspaceId}`,
  mcpTokens: (workspaceId: string) => `mcp-tokens:${workspaceId}`,
  oauthClients: (workspaceId: string) => `oauth-clients:${workspaceId}`,
  actions: (workspaceId: string) => `actions:${workspaceId}`,
  secrets: (workspaceId: string) => `secrets:${workspaceId}`,
  auditLogs: (workspaceId: string, page?: number) => 
    `audit-logs:${workspaceId}:${page || 1}`,
  executions: (workspaceId: string, page?: number) => 
    `executions:${workspaceId}:${page || 1}`,
  knowledgeBase: (workspaceId: string) => `knowledge-base:${workspaceId}`,
}

/**
 * Cache TTL constants
 */
export const cacheTTL = {
  workspaces: 30000, // 30 seconds
  stats: 15000,      // 15 seconds (faster refresh for stats)
  tokens: 10000,     // 10 seconds  
  actions: 30000,    // 30 seconds
  auditLogs: 60000,  // 1 minute
  executions: 30000, // 30 seconds
  knowledgeBase: 30000, // 30 seconds
}