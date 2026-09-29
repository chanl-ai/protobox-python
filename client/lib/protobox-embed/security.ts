// ProtoBox Embed Security Utilities

export interface SecurityConfig {
  // Allowed parent domains that can embed the iframe
  allowedOrigins: string[]
  // Whether to allow localhost origins in development
  allowLocalhost?: boolean
  // Custom validation function
  customValidator?: (origin: string, data: any) => boolean
  // Enable debug logging
  debug?: boolean
}

export class EmbedSecurity {
  private config: SecurityConfig
  private trustedOrigins: Set<string>

  constructor(config: SecurityConfig) {
    this.config = config
    this.trustedOrigins = new Set(config.allowedOrigins)
    
    // Add localhost origins if enabled
    if (config.allowLocalhost) {
      this.trustedOrigins.add('http://localhost:3000')
      this.trustedOrigins.add('http://localhost:3001')
      this.trustedOrigins.add('http://127.0.0.1:3000')
      this.trustedOrigins.add('http://127.0.0.1:3001')
    }
  }

  /**
   * Validate if an origin is allowed to communicate with the iframe
   */
  validateOrigin(origin: string): boolean {
    if (!origin) return false

    // Check exact match
    if (this.trustedOrigins.has(origin)) {
      this.log(`Origin ${origin} is trusted (exact match)`)
      return true
    }

    // Check wildcard domains (e.g., *.example.com)
    for (const trusted of this.trustedOrigins) {
      if (trusted.startsWith('*')) {
        const domain = trusted.slice(1) // Remove *
        if (origin.endsWith(domain)) {
          this.log(`Origin ${origin} is trusted (wildcard match: ${trusted})`)
          return true
        }
      }
    }

    // Custom validation
    if (this.config.customValidator) {
      const customResult = this.config.customValidator(origin, null)
      if (customResult) {
        this.log(`Origin ${origin} is trusted (custom validator)`)
        return true
      }
    }

    this.log(`Origin ${origin} is NOT trusted`, 'warn')
    return false
  }

  /**
   * Validate a message event
   */
  validateMessage(event: MessageEvent): boolean {
    // Validate origin
    if (!this.validateOrigin(event.origin)) {
      return false
    }

    // Validate message structure
    if (!event.data || typeof event.data !== 'object') {
      this.log('Invalid message structure', 'warn')
      return false
    }

    // Additional custom validation
    if (this.config.customValidator) {
      return this.config.customValidator(event.origin, event.data)
    }

    return true
  }

  /**
   * Add a trusted origin at runtime
   */
  addTrustedOrigin(origin: string): void {
    this.trustedOrigins.add(origin)
    this.log(`Added trusted origin: ${origin}`)
  }

  /**
   * Remove a trusted origin at runtime
   */
  removeTrustedOrigin(origin: string): void {
    this.trustedOrigins.delete(origin)
    this.log(`Removed trusted origin: ${origin}`)
  }

  /**
   * Get all trusted origins
   */
  getTrustedOrigins(): string[] {
    return Array.from(this.trustedOrigins)
  }

  /**
   * Generate a secure nonce for CSP
   */
  static generateNonce(): string {
    const array = new Uint8Array(16)
    crypto.getRandomValues(array)
    return btoa(String.fromCharCode.apply(null, Array.from(array)))
  }

  /**
   * Generate CSP header for iframe
   */
  static generateCSP(nonce: string, allowedOrigins: string[]): string {
    const frameSources = allowedOrigins.length > 0 
      ? allowedOrigins.join(' ') 
      : "'none'"
    
    return [
      `default-src 'self'`,
      `script-src 'self' 'nonce-${nonce}'`,
      `style-src 'self' 'unsafe-inline'`, // Allow inline styles for theming
      `img-src 'self' data: https:`,
      `font-src 'self'`,
      `connect-src 'self' ${allowedOrigins.join(' ')}`,
      `frame-ancestors ${frameSources}`,
      `base-uri 'self'`,
      `form-action 'self'`,
    ].join('; ')
  }

  /**
   * Sanitize user-provided data
   */
  static sanitizeData<T extends Record<string, any>>(data: T): T {
    const sanitized = {} as T
    
    for (const [key, value] of Object.entries(data)) {
      if (typeof value === 'string') {
        // Basic XSS prevention
        sanitized[key as keyof T] = value
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#x27;')
          .replace(/\//g, '&#x2F;') as T[keyof T]
      } else if (typeof value === 'object' && value !== null) {
        // Recursively sanitize nested objects
        sanitized[key as keyof T] = this.sanitizeData(value)
      } else {
        // Safe types (numbers, booleans, null)
        sanitized[key as keyof T] = value
      }
    }
    
    return sanitized
  }

  private log(message: string, level: 'info' | 'warn' | 'error' = 'info'): void {
    if (!this.config.debug) return
    
    const prefix = '[ProtoBox Security]'
    switch (level) {
      case 'warn':
        break
      case 'error':
        break
      default:
    }
  }
}

// Default security config for production
export const DEFAULT_SECURITY_CONFIG: SecurityConfig = {
  allowedOrigins: [
    'http://localhost:3010',
  ],
  allowLocalhost: false,
  debug: false,
}

// Development security config
export const DEV_SECURITY_CONFIG: SecurityConfig = {
  allowedOrigins: [
    'http://localhost:3010',
  ],
  allowLocalhost: true,
  debug: true,
}