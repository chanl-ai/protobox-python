/**
 * Enhanced production-safe console utilities
 * - Automatically disabled in production builds
 * - Can be enabled in production via runtime controls
 * - Supports different debug levels and namespaces
 */

type LogLevel = 'debug' | 'log' | 'info' | 'warn' | 'error';
type LogNamespace = string;

class Logger {
  private isDevelopment = process.env.NODE_ENV === 'development';
  private debugEnabled = false;
  private enabledNamespaces = new Set<string>();
  private logLevel: LogLevel = 'log';
  private sessionId = Math.random().toString(36).substring(7);

  constructor() {
    if (typeof window !== 'undefined') {
      // Check for debug flags in localStorage or URL
      this.initializeFromStorage();
      this.initializeFromURL();
    }
  }

  /**
   * Initialize debug settings from localStorage
   */
  private initializeFromStorage() {
    try {
      const debugFlag = localStorage.getItem('debug');
      const debugNamespaces = localStorage.getItem('debug-namespaces');
      const debugLevel = localStorage.getItem('debug-level') as LogLevel;
      
      if (debugFlag === 'true') {
        this.debugEnabled = true;
      }
      
      if (debugNamespaces) {
        debugNamespaces.split(',').forEach(ns => this.enabledNamespaces.add(ns.trim()));
      }
      
      if (debugLevel) {
        this.logLevel = debugLevel;
      }
    } catch (e) {
      // Ignore storage errors
    }
  }

  /**
   * Initialize debug settings from URL parameters
   */
  private initializeFromURL() {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const debugFlag = urlParams.get('debug');
      const debugNamespaces = urlParams.get('debug-namespaces');
      
      if (debugFlag === 'true' || debugFlag === '1') {
        this.debugEnabled = true;
      }
      
      if (debugNamespaces) {
        debugNamespaces.split(',').forEach(ns => this.enabledNamespaces.add(ns.trim()));
      }
    } catch (e) {
      // Ignore URL parsing errors
    }
  }

  /**
   * Check if logging should be enabled for this namespace and level
   */
  private shouldLog(level: LogLevel, namespace?: string): boolean {
    // Always allow errors and warnings
    if (level === 'error' || level === 'warn') {
      return true;
    }
    
    // In development, allow all logs
    if (this.isDevelopment) {
      return true;
    }
    
    // In production, only allow if debug is enabled
    if (!this.debugEnabled) {
      return false;
    }
    
    // Check namespace filtering
    if (namespace && this.enabledNamespaces.size > 0) {
      return this.enabledNamespaces.has(namespace) || this.enabledNamespaces.has('*');
    }
    
    // Check log level
    const levels: LogLevel[] = ['debug', 'log', 'info', 'warn', 'error'];
    const currentLevelIndex = levels.indexOf(this.logLevel);
    const requestedLevelIndex = levels.indexOf(level);
    
    return requestedLevelIndex >= currentLevelIndex;
  }

  /**
   * Create a namespaced logger
   */
  namespace(namespace: LogNamespace) {
    return {
      debug: (...args: any[]) => this.debug(...args, { namespace }),
      log: (...args: any[]) => this.log(...args, { namespace }),
      info: (...args: any[]) => this.info(...args, { namespace }),
      warn: (...args: any[]) => this.warn(...args, { namespace }),
      error: (...args: any[]) => this.error(...args, { namespace }),
      table: (data: any) => this.table(data, { namespace }),
      group: (label: string) => this.group(label, { namespace }),
      groupEnd: () => this.groupEnd({ namespace }),
    };
  }

  /**
   * Format log message with metadata
   */
  private formatMessage(args: any[], options?: { namespace?: string }) {
    const timestamp = new Date().toISOString();
    const prefix = [];
    
    if (this.debugEnabled && !this.isDevelopment) {
      prefix.push(`🐛[${this.sessionId}]`);
    }
    
    if (options?.namespace) {
      prefix.push(`[${options.namespace}]`);
    }
    
    if (this.debugEnabled) {
      prefix.push(`[${timestamp}]`);
    }
    
    return prefix.length > 0 ? [prefix.join(' '), ...args] : args;
  }

  // Core logging methods
  debug(...args: any[]) {
    const options = typeof args[args.length - 1] === 'object' && args[args.length - 1]?.namespace 
      ? args.pop() : undefined;
    
    if (this.shouldLog('debug', options?.namespace)) {
      console.debug(...this.formatMessage(args, options));
    }
  }

  log(...args: any[]) {
    const options = typeof args[args.length - 1] === 'object' && args[args.length - 1]?.namespace 
      ? args.pop() : undefined;
    
    if (this.shouldLog('log', options?.namespace)) {
      console.log(...this.formatMessage(args, options));
    }
  }

  info(...args: any[]) {
    const options = typeof args[args.length - 1] === 'object' && args[args.length - 1]?.namespace 
      ? args.pop() : undefined;
    
    if (this.shouldLog('info', options?.namespace)) {
      console.info(...this.formatMessage(args, options));
    }
  }

  warn(...args: any[]) {
    const options = typeof args[args.length - 1] === 'object' && args[args.length - 1]?.namespace 
      ? args.pop() : undefined;
    
    if (this.shouldLog('warn', options?.namespace)) {
      console.warn(...this.formatMessage(args, options));
    }
  }

  error(...args: any[]) {
    const options = typeof args[args.length - 1] === 'object' && args[args.length - 1]?.namespace 
      ? args.pop() : undefined;
    
    if (this.shouldLog('error', options?.namespace)) {
      console.error(...this.formatMessage(args, options));
    }
  }

  table(data: any, options?: { namespace?: string }) {
    if (this.shouldLog('log', options?.namespace)) {
      if (options?.namespace) {
        console.log(`[${options.namespace}] Table:`);
      }
      console.table?.(data);
    }
  }

  group(label: string, options?: { namespace?: string }) {
    if (this.shouldLog('log', options?.namespace)) {
      console.group?.(...this.formatMessage([label], options));
    }
  }

  groupEnd(options?: { namespace?: string }) {
    if (this.shouldLog('log', options?.namespace)) {
      console.groupEnd?.();
    }
  }

  // Runtime control methods
  enableDebug(enabled = true) {
    this.debugEnabled = enabled;
    if (typeof window !== 'undefined') {
      localStorage.setItem('debug', enabled.toString());
    }
    return this;
  }

  enableNamespace(...namespaces: string[]) {
    namespaces.forEach(ns => this.enabledNamespaces.add(ns));
    if (typeof window !== 'undefined') {
      localStorage.setItem('debug-namespaces', Array.from(this.enabledNamespaces).join(','));
    }
    return this;
  }

  disableNamespace(...namespaces: string[]) {
    namespaces.forEach(ns => this.enabledNamespaces.delete(ns));
    if (typeof window !== 'undefined') {
      localStorage.setItem('debug-namespaces', Array.from(this.enabledNamespaces).join(','));
    }
    return this;
  }

  setLevel(level: LogLevel) {
    this.logLevel = level;
    if (typeof window !== 'undefined') {
      localStorage.setItem('debug-level', level);
    }
    return this;
  }

  clearDebugSettings() {
    this.debugEnabled = false;
    this.enabledNamespaces.clear();
    this.logLevel = 'log';
    if (typeof window !== 'undefined') {
      localStorage.removeItem('debug');
      localStorage.removeItem('debug-namespaces');
      localStorage.removeItem('debug-level');
    }
    return this;
  }

  // Status methods
  isDebugEnabled() {
    return this.isDevelopment || this.debugEnabled;
  }

  getStatus() {
    return {
      isDevelopment: this.isDevelopment,
      debugEnabled: this.debugEnabled,
      enabledNamespaces: Array.from(this.enabledNamespaces),
      logLevel: this.logLevel,
      sessionId: this.sessionId
    };
  }
}

// Create singleton instance
const logger = new Logger();

// Make logger available globally for debugging
if (typeof window !== 'undefined') {
  (window as any).__logger = logger;
}

// Export both named and default
export { logger, Logger };
export default logger;