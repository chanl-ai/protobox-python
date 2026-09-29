/**
 * Middleware exports for ProtoboxClient
 */

export { loggingMiddleware } from './logging'
export { analyticsMiddleware } from './analytics'
export { errorTrackingMiddleware } from './error-tracking'

/**
 * Initialize default middlewares for ProtoboxClient
 * This should be called once during app initialization
 */
export function initializeMiddlewares() {
  // Lazy import to avoid circular dependencies
  const { protoboxClient } = require('../protobox-client')
  const { loggingMiddleware } = require('./logging')
  const { errorTrackingMiddleware } = require('./error-tracking')

  // Add default middlewares
  protoboxClient.use(loggingMiddleware)
  protoboxClient.use(errorTrackingMiddleware)

  // Analytics middleware is optional (only if gtag is available)
  if (typeof window !== 'undefined' && (window as any).gtag) {
    const { analyticsMiddleware } = require('./analytics')
    protoboxClient.use(analyticsMiddleware)
  }
}

