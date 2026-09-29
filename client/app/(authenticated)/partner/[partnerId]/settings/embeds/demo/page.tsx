"use client"

import { useEffect, useRef, useState, use } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  ProtoBoxParentClient, 
  createProtoBoxIframe,
  Integration,
  ReadyData,
  ErrorData
} from "@/lib/protobox-embed"
import { 
  AlertCircle, 
  CheckCircle2, 
  RefreshCw, 
  Sun, 
  Moon,
  Filter,
  Code
} from "lucide-react"

interface EmbedDemoPageProps {
  params: Promise<{ partnerId: string }>
}

export default function EmbedDemoPage({ params }: EmbedDemoPageProps) {
  const { partnerId } = use(params)
  const iframeContainerRef = useRef<HTMLDivElement>(null)
  const [client, setClient] = useState<ProtoBoxParentClient | null>(null)
  const [isReady, setIsReady] = useState(false)
  const [readyData, setReadyData] = useState<ReadyData | null>(null)
  const [theme, setTheme] = useState<'light' | 'dark'>('light')
  const [connectedIntegrations, setConnectedIntegrations] = useState<Integration[]>([])
  const [messages, setMessages] = useState<Array<{ time: string, type: string, data?: any }>>([])
  const [error, setError] = useState<ErrorData | null>(null)

  useEffect(() => {
    if (!iframeContainerRef.current) return

    // Clear any existing content
    iframeContainerRef.current.innerHTML = ''

    // Create iframe
    const iframe = createProtoBoxIframe({
      src: `http://localhost:3001/integrations?partner_id=${partnerId}&user_id=demo_user&theme=${theme}`,
      width: '100%',
      height: '600',
      className: 'border rounded-lg'
    })

    // Add to container
    iframeContainerRef.current.appendChild(iframe)

    // Reset state
    setIsReady(false)
    setReadyData(null)
    setError(null)

    // Create parent client
    const parentClient = new ProtoBoxParentClient({
      iframe,
      debug: true,
      onReady: (data) => {
        setIsReady(true)
        setReadyData(data)
        addMessage('Ready', data)
      },
      onError: (error) => {
        setError(error)
        addMessage('Error', error)
      },
      onIntegrationConnected: (integration) => {
        setConnectedIntegrations(prev => [...prev, integration])
        addMessage('Integration Connected', integration)
      },
      onIntegrationDisconnected: (integration) => {
        setConnectedIntegrations(prev => prev.filter(i => i.id !== integration.id))
        addMessage('Integration Disconnected', integration)
      },
      onHeightChanged: (height) => {
        iframe.height = String(height)
        addMessage('Height Changed', { height })
      },
      onNavigate: (path, target) => {
        addMessage('Navigate', { path, target })
        if (target === '_blank') {
          window.open(path, target)
        }
      },
      onMessage: (message) => {
        addMessage(message.type, message.data)
      }
    })

    setClient(parentClient)

    return () => {
      parentClient.destroy()
      if (iframeContainerRef.current?.contains(iframe)) {
        iframeContainerRef.current.removeChild(iframe)
      }
    }
  }, [partnerId, theme])

  const addMessage = (type: string, data?: any) => {
    setMessages(prev => [...prev, {
      time: new Date().toLocaleTimeString(),
      type,
      data
    }].slice(-20)) // Keep last 20 messages
  }

  const handleRefresh = () => {
    client?.refresh()
    addMessage('Parent Action', { action: 'refresh' })
  }

  const handleThemeToggle = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
    client?.updateTheme(newTheme)
    addMessage('Parent Action', { action: 'updateTheme', theme: newTheme })
  }

  const handleFilter = (status: 'all' | 'connected' | 'disconnected') => {
    const filter = status === 'all' 
      ? {} 
      : { status: [status as 'connected' | 'disconnected'] }
    client?.filterIntegrations(filter)
    addMessage('Parent Action', { action: 'filter', filter })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Embed Demo</h1>
        <p className="text-muted-foreground">
          Interactive demo of the ProtoBox embed with PostMessage API
        </p>
      </div>

      {/* Status */}
      <div className="flex items-center gap-4">
        <Badge variant={isReady ? "default" : "secondary"} className="gap-1">
          {isReady ? (
            <>
              <CheckCircle2 className="h-3 w-3" />
              Ready
            </>
          ) : (
            <>
              <AlertCircle className="h-3 w-3" />
              Not Ready
            </>
          )}
        </Badge>
        {readyData && (
          <>
            <Badge variant="outline">Mode: {readyData.mode}</Badge>
            {readyData.integrations_count !== undefined && (
              <Badge variant="outline">Integrations: {readyData.integrations_count}</Badge>
            )}
          </>
        )}
        {connectedIntegrations.length > 0 && (
          <Badge variant="outline" className="bg-green-50">
            Connected: {connectedIntegrations.length}
          </Badge>
        )}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <strong>{error.code}:</strong> {error.message}
          </AlertDescription>
        </Alert>
      )}

      {/* Controls */}
      <Card>
        <CardHeader>
          <CardTitle>Parent Controls</CardTitle>
          <CardDescription>
            Control the iframe from the parent window
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            <Button 
              onClick={handleRefresh} 
              disabled={!isReady}
              variant="outline"
              size="sm"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Button 
              onClick={handleThemeToggle} 
              disabled={!isReady}
              variant="outline"
              size="sm"
            >
              {theme === 'light' ? (
                <Moon className="h-4 w-4 mr-2" />
              ) : (
                <Sun className="h-4 w-4 mr-2" />
              )}
              Toggle Theme
            </Button>
          </div>
          
          <div className="space-y-2">
            <p className="text-sm font-medium">Filter Integrations:</p>
            <div className="flex gap-2">
              <Button 
                onClick={() => handleFilter('all')} 
                disabled={!isReady}
                variant="outline"
                size="sm"
              >
                <Filter className="h-4 w-4 mr-2" />
                All
              </Button>
              <Button 
                onClick={() => handleFilter('connected')} 
                disabled={!isReady}
                variant="outline"
                size="sm"
              >
                Connected Only
              </Button>
              <Button 
                onClick={() => handleFilter('disconnected')} 
                disabled={!isReady}
                variant="outline"
                size="sm"
              >
                Available Only
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Embed */}
      <Card>
        <CardHeader>
          <CardTitle>Embed Preview</CardTitle>
        </CardHeader>
        <CardContent>
          <div ref={iframeContainerRef} />
        </CardContent>
      </Card>

      {/* Message Log */}
      <Card>
        <CardHeader>
          <CardTitle>Message Log</CardTitle>
          <CardDescription>
            Real-time PostMessage communication between parent and iframe
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-muted rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs space-y-1">
            {messages.length === 0 ? (
              <p className="text-muted-foreground">No messages yet...</p>
            ) : (
              messages.map((msg, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-muted-foreground">{msg.time}</span>
                  <span className="font-semibold">{msg.type}:</span>
                  <span className="text-muted-foreground">
                    {msg.data ? JSON.stringify(msg.data, null, 2) : 'no data'}
                  </span>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Connected Integrations */}
      {connectedIntegrations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Connected Integrations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {connectedIntegrations.map(integration => (
                <div key={integration.id} className="flex items-center justify-between p-2 border rounded">
                  <div>
                    <p className="font-medium">{integration.name}</p>
                    <p className="text-sm text-muted-foreground">{integration.description}</p>
                  </div>
                  <Badge variant="outline" className="bg-green-50">
                    Connected
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Implementation Guide */}
      <Tabs defaultValue="basic" className="w-full">
        <TabsList>
          <TabsTrigger value="basic">Basic Setup</TabsTrigger>
          <TabsTrigger value="advanced">Advanced Usage</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>
        
        <TabsContent value="basic" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Basic Implementation</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                <code>{`import { ProtoBoxParentClient, createProtoBoxIframe } from '@protobox/embed'

// Create iframe
const iframe = createProtoBoxIframe({
  src: 'http://localhost:3010/integrations?partner_id=YOUR_ID&user_id=USER_ID',
  width: '100%',
  height: '600'
})

// Add to page
document.getElementById('container').appendChild(iframe)

// Create client
const client = new ProtoBoxParentClient({
  iframe,
  onReady: (data) => {
  },
  onIntegrationConnected: (integration) => {
  }
})`}</code>
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="advanced" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Advanced Features</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">Custom Event Handlers</h4>
                <pre className="bg-muted p-3 rounded text-sm">
                  <code>{`// Listen for custom events
client.on('protobox-custom-event', (data) => {
})

// Send custom messages
client.sendMessage('my-custom-message', { 
  action: 'custom',
  payload: data 
})`}</code>
                </pre>
              </div>
              
              <div>
                <h4 className="font-medium mb-2">Auto-Height Adjustment</h4>
                <pre className="bg-muted p-3 rounded text-sm">
                  <code>{`// Height automatically adjusts
onHeightChanged: (height) => {
  iframe.height = height
}`}</code>
                </pre>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Security Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                <code>{`const client = new ProtoBoxParentClient({
  iframe,
  security: {
    allowedOrigins: [
      'http://localhost:3010',
    ],
    allowLocalhost: false, // Disable in production
    customValidator: (origin, data) => {
      // Custom validation logic
      return myCustomCheck(origin)
    }
  }
})`}</code>
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}