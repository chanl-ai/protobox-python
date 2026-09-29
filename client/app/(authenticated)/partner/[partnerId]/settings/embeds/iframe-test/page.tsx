"use client"

import { useState, useRef, useEffect, use } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  AlertCircle,
  RefreshCw,
  Code,
  Smartphone,
  Monitor
} from "lucide-react"
import { toast, Toaster } from "sonner"

interface IframeTestPageProps {
  params: Promise<{ partnerId: string }>
}

export default function IframeTestPage({ params }: IframeTestPageProps) {
  const { partnerId } = use(params)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [iframeHeight, setIframeHeight] = useState('600px')
  const [deviceView, setDeviceView] = useState<'desktop' | 'tablet' | 'mobile'>('desktop')
  const [events, setEvents] = useState<Array<{ time: Date; type: string; data: any }>>([])

  // Test configuration - using same app embed route
  const embedUrl = process.env.NODE_ENV === 'development' 
    ? 'http://localhost:3001' // Same app, different route
    : window.location.origin // In production, same domain
    
  const iframeSrc = `${embedUrl}/marketplace?partner_id=${partnerId}&user_id=test_user_123&theme=light`

  // Handle messages from iframe
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // In dev, accept localhost origins
      if (!event.origin.startsWith(embedUrl) && !event.origin.includes('localhost')) return

      const { type, data } = event.data
      
      // Log event
      setEvents(prev => [...prev.slice(-9), { 
        time: new Date(), 
        type, 
        data 
      }])

      switch (type) {
        case 'protobox-ready':
          toast.success('ProtoBox embed loaded successfully')
          break

        case 'protobox-resize':
          if (data.height) {
            setIframeHeight(`${data.height}px`)
          }
          break

        case 'protobox-integration-connected':
          toast.success(`Connected ${data.integration.name}!`)
          break

        case 'protobox-integration-disconnected':
          toast.info(`Disconnected ${data.integration.name}`)
          break

        case 'protobox-error':
          toast.error(`Error: ${data.error.message}`)
          break
      }
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [embedUrl])

  const sendMessage = (message: any) => {
    if (iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage(message, embedUrl)
    }
  }

  const refresh = () => {
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src
    }
  }

  const deviceWidths = {
    desktop: '100%',
    tablet: '768px',
    mobile: '375px'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">iFrame Embed Test</h1>
        <p className="text-muted-foreground">
          Testing the ProtoBox iframe embed with PostMessage communication
        </p>
      </div>

      {/* Embed Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Embed Configuration</CardTitle>
          <CardDescription>
            Current iframe settings and controls
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium">Embed URL:</span>
              <code className="flex-1 px-2 py-1 bg-muted rounded text-xs">{iframeSrc}</code>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium">Current Height:</span>
              <code className="px-2 py-1 bg-muted rounded text-xs">{iframeHeight}</code>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={refresh}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => sendMessage({ type: 'protobox-refresh' })}
              >
                Send Refresh Message
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Device Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Embed Preview</span>
            <div className="flex gap-2">
              <Button
                variant={deviceView === 'desktop' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDeviceView('desktop')}
              >
                <Monitor className="h-4 w-4" />
              </Button>
              <Button
                variant={deviceView === 'tablet' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDeviceView('tablet')}
              >
                <Smartphone className="h-4 w-4 rotate-90" />
              </Button>
              <Button
                variant={deviceView === 'mobile' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setDeviceView('mobile')}
              >
                <Smartphone className="h-4 w-4" />
              </Button>
            </div>
          </CardTitle>
          <CardDescription>
            Responsive preview of the ProtoBox embed
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex justify-center">
            <div 
              className="border rounded-lg overflow-hidden transition-all duration-300"
              style={{ width: deviceWidths[deviceView] }}
            >
              <iframe
                ref={iframeRef}
                src={iframeSrc}
                width="100%"
                height={iframeHeight}
                frameBorder="0"
                allow="clipboard-write"
                title="ProtoBox Integrations"
                className="block"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Event Log */}
      <Card>
        <CardHeader>
          <CardTitle>PostMessage Events</CardTitle>
          <CardDescription>
            Real-time log of messages between iframe and parent
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {events.length === 0 ? (
              <p className="text-sm text-muted-foreground">No events yet...</p>
            ) : (
              events.map((event, i) => (
                <div key={i} className="text-xs font-mono p-2 bg-muted rounded">
                  <span className="text-muted-foreground">
                    {event.time.toLocaleTimeString()}
                  </span>
                  {' '}
                  <span className="font-semibold text-primary">{event.type}</span>
                  {event.data && (
                    <pre className="mt-1 text-muted-foreground">
                      {JSON.stringify(event.data, null, 2)}
                    </pre>
                  )}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Implementation Examples */}
      <Card>
        <CardHeader>
          <CardTitle>Implementation Examples</CardTitle>
          <CardDescription>
            How to implement the iframe embed with wrapper
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="react">
            <TabsList>
              <TabsTrigger value="react">React Component</TabsTrigger>
              <TabsTrigger value="vanilla">Vanilla JS</TabsTrigger>
              <TabsTrigger value="direct">Direct iFrame</TabsTrigger>
            </TabsList>

            <TabsContent value="react">
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                <code>{`import { ProtoBoxEmbed } from '@protobox/embed-react'

function App() {
  return (
    <ProtoBoxEmbed
      partnerId="${partnerId}"
      userId={currentUser.id}
      theme="light"
      onConnect={(integration) => {
        // Your app can now use this integration
      }}
      onError={(error) => {
      }}
    />
  )
}`}</code>
              </pre>
            </TabsContent>

            <TabsContent value="vanilla">
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                <code>{`<div id="protobox-container"></div>

<script>
  const iframe = document.createElement('iframe')
  iframe.src = 'http://localhost:3010/marketplace?partner_id=${partnerId}&user_id=' + userId
  iframe.width = '100%'
  iframe.height = '600'
  iframe.frameBorder = '0'
  
  document.getElementById('protobox-container').appendChild(iframe)
  
  window.addEventListener('message', (event) => {
    if (!event.origin.startsWith('http://localhost:3010')) return
    
    if (event.data.type === 'protobox-integration-connected') {
    }
  })
</script>`}</code>
              </pre>
            </TabsContent>

            <TabsContent value="direct">
              <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                <code>{`<iframe 
  src="http://localhost:3010/marketplace?partner_id=${partnerId}&user_id=USER_ID"
  width="100%"
  height="600"
  frameborder="0"
  allow="clipboard-write">
</iframe>`}</code>
              </pre>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Note</AlertTitle>
        <AlertDescription>
          In production, the iframe will load from your dashboard's domain with proper SSL and security headers.
          The wrapper components handle all PostMessage communication automatically.
        </AlertDescription>
      </Alert>

      <Toaster 
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155'
          }
        }}
      />
    </div>
  )
}