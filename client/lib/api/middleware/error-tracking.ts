/**
 * Error Tracking Middleware for ProtoboxClient
 * Integrates with Sentry for error tracking
 */

import type { Middleware } from '../protobox-client'

export const errorTrackingMiddleware: Middleware = {
  onError: (error, config) => {
    // Capture error in Sentry if available
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      try {
        ;(window as any).Sentry.captureException(error, {
          tags: {
            api_endpoint: config.endpoint,
            api_method: config.method,
          },
          extra: {
            endpoint: config.endpoint,
            method: config.method,
            url: config.url,
          },
        })
      } catch (sentryError) {
        // Silently fail if Sentry not properly initialized
        console.debug('Sentry error tracking failed', sentryError)
      }
    }
    return error
  },
}

