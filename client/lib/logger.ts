/**
 * Centralized Logging System with Sentry Integration
 * 
 * Features:
 * - Environment-based log level control
 * - Structured logging with context metadata
 * - Sentry integration for error tracking
 * - Module-specific loggers
 * - Performance timing utilities
 * - Security-conscious (filters sensitive data)
 */

import { toast } from 'sonner'

// Log levels in order of severity
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  FATAL = 4
}

// Log entry structure
export interface LogEntry {
  level: LogLevel
  message: string
  module: string
  timestamp: Date
  metadata?: Record<string, any>
  error?: Error
  userId?: string
  sessionId?: string
}

// Logger configuration
export interface LoggerConfig {
  level: LogLevel
  enableConsole: boolean
  enableSentry: boolean
  enableToast: boolean
  filterSensitive: boolean
}

// Default configuration based on environment
const getDefaultConfig = (): LoggerConfig => {
  const isDev = process.env.NODE_ENV === 'development'
  const isDebugEnabled = process.env.NEXT_PUBLIC_DEBUG === 'true'
  
  return {
    level: (isDev || isDebugEnabled) ? LogLevel.DEBUG : LogLevel.INFO,
    enableConsole: isDev || isDebugEnabled,
    enableSentry: process.env.NODE_ENV === 'production',
    enableToast: true,
    filterSensitive: true
  }
}

// Sensitive data patterns to filter
const SENSITIVE_PATTERNS = [
  /password/i,
  /token/i,
  /secret/i,
  /key/i,
  /auth/i,
  /credential/i,
  /session/i
]

// Filter sensitive data from objects
const filterSensitiveData = (obj: any): any => {
  if (!obj || typeof obj !== 'object') return obj
  
  if (Array.isArray(obj)) {
    return obj.map(filterSensitiveData)
  }
  
  const filtered: Record<string, any> = {}
  
  for (const [key, value] of Object.entries(obj)) {
    const isSensitive = SENSITIVE_PATTERNS.some(pattern => pattern.test(key))
    
    if (isSensitive) {
      filtered[key] = '[FILTERED]'
    } else if (typeof value === 'object' && value !== null) {
      filtered[key] = filterSensitiveData(value)
    } else {
      filtered[key] = value
    }
  }
  
  return filtered
}

class Logger {
  private config: LoggerConfig
  private module: string
  
  constructor(module: string, config?: Partial<LoggerConfig>) {
    this.module = module
    this.config = { ...getDefaultConfig(), ...config }
  }
  
  // Core logging method
  private logInternal(level: LogLevel, message: string, metadata?: Record<string, any>, error?: Error) {
    // Skip if below configured level
    if (level < this.config.level) return
    
    const entry: LogEntry = {
      level,
      message,
      module: this.module,
      timestamp: new Date(),
      metadata: this.config.filterSensitive ? filterSensitiveData(metadata) : metadata,
      error
    }
    
    // Add user context if available
    if (typeof window !== 'undefined') {
      try {
        // Get user context from auth store if available
        const authStore = (window as any).__authStore?.getState?.()
        if (authStore?.user?.uid) {
          entry.userId = authStore.user.uid
        }
      } catch (e) {
        // Ignore errors getting user context
      }
    }
    
    // Output to console (development)
    if (this.config.enableConsole) {
      this.logToConsole(entry)
    }
    
    // Send to Sentry (production)
    if (this.config.enableSentry && (level >= LogLevel.WARN || error)) {
      this.logToSentry(entry)
    }
    
    // Show toast for user-facing errors
    if (this.config.enableToast && level >= LogLevel.ERROR) {
      this.logToToast(entry)
    }
  }
  
  // Console output with colors and formatting
  private logToConsole(entry: LogEntry) {
    const { level, message, module, metadata, error } = entry
    const timestamp = entry.timestamp.toISOString()
    
    const colors = {
      [LogLevel.DEBUG]: '#6B7280', // gray
      [LogLevel.INFO]: '#3B82F6',  // blue
      [LogLevel.WARN]: '#F59E0B',  // yellow
      [LogLevel.ERROR]: '#EF4444', // red
      [LogLevel.FATAL]: '#DC2626'  // dark red
    }
    
    const levelNames = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL']
    const levelName = levelNames[level]
    const color = colors[level]
    
    console.group(`%c[${levelName}] ${module}`, `color: ${color}; font-weight: bold`)
    console.log(`%c${message}`, `color: ${color}`)
    console.log(`%c${timestamp}`, 'color: #9CA3AF; font-size: 0.8em')
    
    if (metadata && Object.keys(metadata).length > 0) {
      console.log('Metadata:', metadata)
    }
    
    if (error) {
      console.error('Error:', error)
    }
    
    console.groupEnd()
  }
  
  // Sentry integration (placeholder for now)
  private logToSentry(entry: LogEntry) {
    // TODO: Implement Sentry integration
    if (typeof window !== 'undefined' && (window as any).Sentry) {
      const Sentry = (window as any).Sentry
      
      if (entry.error) {
        Sentry.captureException(entry.error, {
          tags: { module: entry.module },
          extra: entry.metadata,
          level: entry.level >= LogLevel.ERROR ? 'error' : 'warning'
        })
      } else {
        Sentry.captureMessage(entry.message, {
          tags: { module: entry.module },
          extra: entry.metadata,
          level: entry.level >= LogLevel.ERROR ? 'error' : 'warning'
        })
      }
    }
  }
  
  // Toast notifications for user-facing issues
  private logToToast(entry: LogEntry) {
    if (typeof window === 'undefined') return
    
    const { level, message } = entry
    
    // Only show user-friendly messages in toasts
    const userMessage = message.replace(/\[.*?\]/g, '').trim() || 'An error occurred'
    
    switch (level) {
      case LogLevel.ERROR:
      case LogLevel.FATAL:
        toast.error(userMessage)
        break
      case LogLevel.WARN:
        toast.warning(userMessage)
        break
      default:
        toast.info(userMessage)
    }
  }
  
  // Public logging methods
  debug(message: string, metadata?: Record<string, any>) {
    this.logInternal(LogLevel.DEBUG, message, metadata)
  }
  
  info(message: string, metadata?: Record<string, any>) {
    this.logInternal(LogLevel.INFO, message, metadata)
  }
  
  warn(message: string, metadata?: Record<string, any>, error?: Error) {
    this.logInternal(LogLevel.WARN, message, metadata, error)
  }
  
  error(message: string, metadata?: Record<string, any>, error?: Error) {
    this.logInternal(LogLevel.ERROR, message, metadata, error)
  }
  
  fatal(message: string, metadata?: Record<string, any>, error?: Error) {
    this.logInternal(LogLevel.FATAL, message, metadata, error)
  }
  
  // Performance timing utility
  time(label: string) {
    if (this.config.enableConsole) {
      console.time(`[${this.module}] ${label}`)
    }
  }
  
  timeEnd(label: string) {
    if (this.config.enableConsole) {
      console.timeEnd(`[${this.module}] ${label}`)
    }
  }
  
  // Backward compatibility methods for existing console.log usage
  log(message: string, ...args: any[]) {
    if (args.length > 0) {
      this.logInternal(LogLevel.DEBUG, message, { args })
    } else {
      this.logInternal(LogLevel.DEBUG, message)
    }
  }
  
  group(message: string, ...args: any[]) {
    if (this.config.enableConsole) {
      if (args.length > 0) {
        console.group(message, ...args)
      } else {
        console.group(message)
      }
    }
  }
  
  groupEnd() {
    if (this.config.enableConsole) {
      console.groupEnd()
    }
  }
  
  table(data: any) {
    if (this.config.enableConsole) {
      console.table(data)
    }
  }
  
  // Create child logger with additional context
  child(childModule: string, metadata?: Record<string, any>): Logger {
    const child = new Logger(`${this.module}:${childModule}`, this.config)
    
    // Override logInternal method to include parent metadata
    const originalLogInternal = child.logInternal.bind(child)
    child.logInternal = (level: LogLevel, message: string, childMetadata?: Record<string, any>, error?: Error) => {
      const combinedMetadata = { ...metadata, ...childMetadata }
      originalLogInternal(level, message, combinedMetadata, error)
    }
    
    return child
  }
}

// Global logger configuration
let globalConfig = getDefaultConfig()

export const configureLogger = (config: Partial<LoggerConfig>) => {
  globalConfig = { ...globalConfig, ...config }
}

// Create module-specific loggers
export const createLogger = (module: string, config?: Partial<LoggerConfig>): Logger => {
  return new Logger(module, { ...globalConfig, ...config })
}

// Pre-configured loggers for common modules
export const loggers = {
  auth: createLogger('Auth'),
  api: createLogger('API'),
  ui: createLogger('UI'),
  workspace: createLogger('Workspace'),
  router: createLogger('Router'),
  store: createLogger('Store'),
  firebase: createLogger('Firebase'),
  performance: createLogger('Performance'),
  security: createLogger('Security')
}

// Main logger instance (backward compatibility)
export const logger = createLogger('App')

// Export a default console replacement for backward compatibility
export default logger

// Export types for TypeScript
export type { LoggerConfig, LogEntry }