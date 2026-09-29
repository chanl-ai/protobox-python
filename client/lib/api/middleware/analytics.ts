/**
 * Analytics Middleware for ProtoboxClient
 * Tracks API usage for analytics purposes
 */

import type { Middleware } from '../protobox-client'

export const analyticsMiddleware: Middleware = {
  onRequest: (config) => {
    // Track API request in analytics
    if (typeof window !== 'undefined' && (window as any).gtag) {
      try {
        ;(window as any).gtag('event', 'api_request', {
          event_category: 'API',
          event_label: config.endpoint,
          method: config.method,
        })
      } catch (error) {
        // Silently fail if analytics not available
      }
    }
    return config
  },

  onResponse: (response, data) => {
    // Track successful API response
    if (typeof window !== 'undefined' && (window as any).gtag && response.ok) {
      try {
        ;(window as any).gtag('event', 'api_response', {
          event_category: 'API',
          event_label: response.status.toString(),
          value: response.status,
        })
      } catch (error) {
        // Silently fail if analytics not available
      }
    }
    return data
  },

  onError: (error, config) => {
    // Track API errors
    if (typeof window !== 'undefined' && (window as any).gtag) {
      try {
        ;(window as any).gtag('event', 'api_error', {
          event_category: 'API',
          event_label: config.endpoint,
          value: 1,
        })
      } catch (error) {
        // Silently fail if analytics not available
      }
    }
    return error
  },
}

