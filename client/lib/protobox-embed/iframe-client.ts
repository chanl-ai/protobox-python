// ProtoBox Iframe Client - runs inside the iframe
import { 
  ProtoBoxMessage, 
  IFRAME_MESSAGES, 
  PARENT_MESSAGES,
  isProtoBoxMessage,
  isParentMessage,
  Integration,
  ErrorData,
  ReadyData,
  HeightData,
  ConfigData,
  FilterData
} from './message-types'
import { EmbedSecurity, SecurityConfig } from './security'

export interface IframeClientConfig {
  partnerId: string
  userId: string
  security?: SecurityConfig
  onMessage?: (message: ProtoBoxMessage) => void
  debug?: boolean
}

export class ProtoBoxIframeClient {
  private config: IframeClientConfig
  private security: EmbedSecurity
  private parentOrigin: string | null = null
  private messageQueue: ProtoBoxMessage[] = []
  private isReady = false
  private listeners: Map<string, Set<(data: any) => void>> = new Map()

  constructor(config: IframeClientConfig) {
    this.config = config
    
    // Initialize security
    const securityConfig = config.security || {
      allowedOrigins: ['*'], // In iframe, we typically allow any parent
      allowLocalhost: true,
      debug: config.debug
    }
    this.security = new EmbedSecurity(securityConfig)
    
    // Set up message listener
    this.setupMessageListener()
    
    // Detect parent origin
    this.detectParentOrigin()
  }

  /**
   * Initialize the iframe client and send ready message
   */
  async initialize(data?: Partial<ReadyData>): Promise<void> {
    try {
      // Send ready message
      this.sendMessage(IFRAME_MESSAGES.READY, {
        mode: 'production',
        ...data
      })
      
      this.isReady = true
      
      // Send any queued messages
      this.flushMessageQueue()
    } catch (error) {
      this.sendError('INIT_ERROR', 'Failed to initialize iframe client')
    }
  }

  /**
   * Send a message to the parent window
   */
  sendMessage(type: string, data?: any): void {
    const message: ProtoBoxMessage = {
      type,
      data: data ? EmbedSecurity.sanitizeData(data) : undefined,
      timestamp: Date.now(),
      version: '1.0.0'
    }
    
    if (!this.isReady && type !== IFRAME_MESSAGES.READY && type !== IFRAME_MESSAGES.ERROR) {
      // Queue messages until ready
      this.messageQueue.push(message)
      return
    }
    
    this.postMessage(message)
  }

  /**
   * Send an error message
   */
  sendError(code: string, message: string, details?: any): void {
    const errorData: ErrorData = {
      code,
      message,
      details
    }
    this.sendMessage(IFRAME_MESSAGES.ERROR, errorData)
  }

  /**
   * Listen for messages from parent
   */
  on(type: string, callback: (data: any) => void): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set())
    }
    
    this.listeners.get(type)!.add(callback)
    
    // Return unsubscribe function
    return () => {
      this.listeners.get(type)?.delete(callback)
    }
  }

  /**
   * Update iframe height based on content
   */
  updateHeight(): void {
    const height = document.body.scrollHeight
    const data: HeightData = { height }
    this.sendMessage(IFRAME_MESSAGES.HEIGHT_CHANGED, data)
  }

  /**
   * Auto-update height on changes
   */
  enableAutoHeight(): void {
    // Initial height
    this.updateHeight()
    
    // Watch for changes
    const observer = new ResizeObserver(() => {
      this.updateHeight()
    })
    
    observer.observe(document.body)
    
    // Also update on DOM changes
    const mutationObserver = new MutationObserver(() => {
      this.updateHeight()
    })
    
    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true
    })
  }

  /**
   * Handle OAuth flow start
   */
  startOAuth(integration: string, scopes?: string[]): void {
    this.sendMessage(IFRAME_MESSAGES.OAUTH_STARTING, {
      integration,
      scopes
    })
  }

  /**
   * Handle integration connection
   */
  onIntegrationConnected(integration: Integration): void {
    this.sendMessage(IFRAME_MESSAGES.INTEGRATION_CONNECTED, { integration })
  }

  /**
   * Handle integration disconnection
   */
  onIntegrationDisconnected(integration: Integration): void {
    this.sendMessage(IFRAME_MESSAGES.INTEGRATION_DISCONNECTED, { integration })
  }

  /**
   * Request navigation
   */
  navigate(path: string, target?: string): void {
    this.sendMessage(IFRAME_MESSAGES.NAVIGATE, { path, target })
  }

  private setupMessageListener(): void {
    window.addEventListener('message', (event) => {
      // Validate message
      if (!this.security.validateMessage(event)) {
        return
      }
      
      const message = event.data
      if (!isProtoBoxMessage(message) || !isParentMessage(message.type)) {
        return
      }
      
      // Store parent origin
      if (!this.parentOrigin) {
        this.parentOrigin = event.origin
        this.log(`Parent origin detected: ${this.parentOrigin}`)
      }
      
      // Handle message
      this.handleMessage(message)
      
      // Call custom handler
      if (this.config.onMessage) {
        this.config.onMessage(message)
      }
    })
  }

  private handleMessage(message: ProtoBoxMessage): void {
    this.log(`Received message: ${message.type}`, message.data)
    
    // Emit to listeners
    const listeners = this.listeners.get(message.type)
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(message.data)
        } catch (error) {
        }
      })
    }
    
    // Handle built-in messages
    switch (message.type) {
      case PARENT_MESSAGES.REFRESH:
        window.location.reload()
        break
        
      case PARENT_MESSAGES.UPDATE_THEME:
        const theme = message.data?.theme || 'light'
        document.documentElement.classList.remove('light', 'dark')
        document.documentElement.classList.add(theme)
        break
        
      case PARENT_MESSAGES.SET_CONFIG:
        this.handleConfigUpdate(message.data as ConfigData)
        break
    }
  }

  private handleConfigUpdate(config: ConfigData): void {
    // Update theme
    if (config.theme) {
      document.documentElement.classList.remove('light', 'dark', 'auto')
      document.documentElement.classList.add(config.theme)
    }
    
    // Emit config update event
    const listeners = this.listeners.get('config-updated')
    if (listeners) {
      listeners.forEach(callback => callback(config))
    }
  }

  private detectParentOrigin(): void {
    // Try to detect parent origin from document.referrer
    if (document.referrer) {
      try {
        const url = new URL(document.referrer)
        this.parentOrigin = url.origin
        this.log(`Parent origin detected from referrer: ${this.parentOrigin}`)
      } catch (error) {
        this.log('Failed to parse referrer', error)
      }
    }
  }

  private postMessage(message: ProtoBoxMessage): void {
    if (window.parent === window) {
      this.log('Not in iframe context', 'warn')
      return
    }
    
    const targetOrigin = this.parentOrigin || '*'
    window.parent.postMessage(message, targetOrigin)
    this.log(`Sent message: ${message.type}`, message.data)
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift()!
      this.postMessage(message)
    }
  }

  private log(message: string, data?: any): void {
    if (!this.config.debug) return
  }
}