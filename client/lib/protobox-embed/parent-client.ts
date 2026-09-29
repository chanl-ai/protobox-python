// ProtoBox Parent Client - runs in the parent window that embeds the iframe
import { 
  ProtoBoxMessage, 
  IFRAME_MESSAGES, 
  PARENT_MESSAGES,
  isProtoBoxMessage,
  isIframeMessage,
  Integration,
  ErrorData,
  ReadyData,
  ConfigData,
  FilterData
} from './message-types'
import { EmbedSecurity, SecurityConfig, DEFAULT_SECURITY_CONFIG } from './security'

export interface ParentClientConfig {
  iframe: HTMLIFrameElement
  security?: SecurityConfig
  onReady?: (data: ReadyData) => void
  onError?: (error: ErrorData) => void
  onIntegrationConnected?: (integration: Integration) => void
  onIntegrationDisconnected?: (integration: Integration) => void
  onHeightChanged?: (height: number) => void
  onNavigate?: (path: string, target?: string) => void
  onMessage?: (message: ProtoBoxMessage) => void
  debug?: boolean
}

export class ProtoBoxParentClient {
  private config: ParentClientConfig
  private security: EmbedSecurity
  private iframe: HTMLIFrameElement
  private iframeOrigin: string
  private isReady = false
  private readyTimeout: NodeJS.Timeout | null = null
  private listeners: Map<string, Set<(data: any) => void>> = new Map()

  constructor(config: ParentClientConfig) {
    this.config = config
    this.iframe = config.iframe
    
    // Get iframe origin
    const iframeSrc = this.iframe.src
    try {
      const url = new URL(iframeSrc)
      this.iframeOrigin = url.origin
    } catch {
      throw new Error('Invalid iframe src URL')
    }
    
    // Initialize security
    const securityConfig = config.security || {
      ...DEFAULT_SECURITY_CONFIG,
      allowedOrigins: [this.iframeOrigin],
      debug: config.debug
    }
    this.security = new EmbedSecurity(securityConfig)
    
    // Set up message listener
    this.setupMessageListener()
    
    // Set ready timeout
    this.setReadyTimeout()
  }

  /**
   * Send a message to the iframe
   */
  sendMessage(type: string, data?: any): void {
    if (!this.isReady && type !== PARENT_MESSAGES.SET_CONFIG) {
      this.log(`Cannot send message ${type} - iframe not ready`, 'warn')
      return
    }
    
    const message: ProtoBoxMessage = {
      type,
      data: data ? EmbedSecurity.sanitizeData(data) : undefined,
      timestamp: Date.now(),
      version: '1.0.0'
    }
    
    this.postMessage(message)
  }

  /**
   * Refresh the iframe content
   */
  refresh(): void {
    this.sendMessage(PARENT_MESSAGES.REFRESH)
  }

  /**
   * Update the theme
   */
  updateTheme(theme: 'light' | 'dark' | 'auto'): void {
    this.sendMessage(PARENT_MESSAGES.UPDATE_THEME, { theme })
  }

  /**
   * Update configuration
   */
  updateConfig(config: ConfigData): void {
    this.sendMessage(PARENT_MESSAGES.SET_CONFIG, config)
  }

  /**
   * Filter integrations
   */
  filterIntegrations(filter: FilterData): void {
    this.sendMessage(PARENT_MESSAGES.FILTER_INTEGRATIONS, filter)
  }

  /**
   * Listen for messages from iframe
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
   * Wait for iframe to be ready
   */
  async waitForReady(timeout = 10000): Promise<ReadyData> {
    if (this.isReady) {
      return Promise.resolve({} as ReadyData)
    }
    
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error('Iframe ready timeout'))
      }, timeout)
      
      const unsubscribe = this.on(IFRAME_MESSAGES.READY, (data: ReadyData) => {
        clearTimeout(timer)
        unsubscribe()
        resolve(data)
      })
    })
  }

  /**
   * Destroy the client and clean up
   */
  destroy(): void {
    if (this.readyTimeout) {
      clearTimeout(this.readyTimeout)
    }
    
    window.removeEventListener('message', this.handleWindowMessage)
    this.listeners.clear()
  }

  private setupMessageListener(): void {
    this.handleWindowMessage = this.handleWindowMessage.bind(this)
    window.addEventListener('message', this.handleWindowMessage)
  }

  private handleWindowMessage(event: MessageEvent): void {
    // Validate origin
    if (event.origin !== this.iframeOrigin) {
      return
    }
    
    // Validate message
    if (!this.security.validateMessage(event)) {
      return
    }
    
    const message = event.data
    if (!isProtoBoxMessage(message) || !isIframeMessage(message.type)) {
      return
    }
    
    // Handle message
    this.handleMessage(message)
    
    // Call custom handler
    if (this.config.onMessage) {
      this.config.onMessage(message)
    }
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
      case IFRAME_MESSAGES.READY:
        this.handleReady(message.data as ReadyData)
        break
        
      case IFRAME_MESSAGES.ERROR:
        this.handleError(message.data as ErrorData)
        break
        
      case IFRAME_MESSAGES.INTEGRATION_CONNECTED:
        if (this.config.onIntegrationConnected) {
          this.config.onIntegrationConnected(message.data.integration)
        }
        break
        
      case IFRAME_MESSAGES.INTEGRATION_DISCONNECTED:
        if (this.config.onIntegrationDisconnected) {
          this.config.onIntegrationDisconnected(message.data.integration)
        }
        break
        
      case IFRAME_MESSAGES.HEIGHT_CHANGED:
        if (this.config.onHeightChanged) {
          this.config.onHeightChanged(message.data.height)
        }
        break
        
      case IFRAME_MESSAGES.NAVIGATE:
        if (this.config.onNavigate) {
          this.config.onNavigate(message.data.path, message.data.target)
        }
        break
    }
  }

  private handleReady(data: ReadyData): void {
    this.isReady = true
    
    if (this.readyTimeout) {
      clearTimeout(this.readyTimeout)
      this.readyTimeout = null
    }
    
    this.log('Iframe is ready', data)
    
    if (this.config.onReady) {
      this.config.onReady(data)
    }
  }

  private handleError(error: ErrorData): void {
    this.log(`Iframe error: ${error.code} - ${error.message}`, error.details, 'error')
    
    if (this.config.onError) {
      this.config.onError(error)
    }
  }

  private setReadyTimeout(): void {
    this.readyTimeout = setTimeout(() => {
      if (!this.isReady) {
        this.handleError({
          code: 'READY_TIMEOUT',
          message: 'Iframe did not send ready message in time'
        })
      }
    }, 10000)
  }

  private postMessage(message: ProtoBoxMessage): void {
    if (!this.iframe.contentWindow) {
      this.log('Iframe contentWindow not available', 'error')
      return
    }
    
    this.iframe.contentWindow.postMessage(message, this.iframeOrigin)
    this.log(`Sent message: ${message.type}`, message.data)
  }

  private log(message: string, data?: any, level: 'info' | 'warn' | 'error' = 'info'): void {
    if (!this.config.debug) return
    
    const prefix = '[ProtoBox Parent]'
    switch (level) {
      case 'warn':
        break
      case 'error':
        break
      default:
    }
  }
}

// Utility function to create iframe with proper attributes
export function createProtoBoxIframe(config: {
  src: string
  width?: string | number
  height?: string | number
  className?: string
  sandbox?: string[]
  allow?: string[]
}): HTMLIFrameElement {
  const iframe = document.createElement('iframe')
  
  iframe.src = config.src
  iframe.width = String(config.width || '100%')
  iframe.height = String(config.height || '600')
  
  if (config.className) {
    iframe.className = config.className
  }
  
  // Security attributes
  iframe.setAttribute('frameborder', '0')
  
  // Sandbox attributes
  const sandbox = config.sandbox || [
    'allow-forms',
    'allow-popups',
    'allow-popups-to-escape-sandbox',
    'allow-same-origin',
    'allow-scripts',
    'allow-storage-access-by-user-activation'
  ]
  iframe.setAttribute('sandbox', sandbox.join(' '))
  
  // Permissions policy
  const allow = config.allow || [
    'clipboard-write',
    'storage-access'
  ]
  iframe.setAttribute('allow', allow.join('; '))
  
  return iframe
}