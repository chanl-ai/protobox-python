/**
 * Logging Middleware for ProtoboxClient
 * Logs all API requests and responses for debugging
 */

import { loggers } from '@/lib/logger'
import type { Middleware } from '../protobox-client'

export const loggingMiddleware: Middleware = {
  onRequest: (config) => {
    loggers.api.debug('API Request', {
      method: config.method,
      endpoint: config.endpoint,
      url: config.url,
      hasBody: !!config.body,
    })
    return config
  },

  onResponse: (response, data) => {
    loggers.api.debug('API Response', {
      status: response.status,
      statusText: response.statusText,
      hasData: !!data,
    })
    return data
  },

  onError: (error, config) => {
    loggers.api.error('API Error', {
      error: error.message,
      endpoint: config.endpoint,
      method: config.method,
    })
    return error
  },
}

