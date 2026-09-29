"use client"

import { useState, use } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { 
  Code,
  Copy,
  RefreshCw,
  Monitor,
  Smartphone,
  Palette,
  Sun,
  Moon,
  AlertCircle
} from "lucide-react"
import { ProtoBoxIntegrations } from "@/components/integrations/protobox-integrations"
import { toast, Toaster } from "sonner"

interface EmbedsPageProps {
  params: Promise<{ partnerId: string }>
}

// Mock integration data for demo
const mockIntegrations = [
  {
    id: "1",
    type: "google_calendar",
    name: "Google Calendar",
    description: "Schedule meetings and manage events",
    is_connected: false,
    status: "disconnected" as const
  },
  {
    id: "2",
    type: "hubspot",
    name: "HubSpot",
    description: "CRM and marketing automation",
    is_connected: true,
    connected_at: "2024-01-15T10:00:00Z",
    status: "connected" as const
  },
  {
    id: "3",
    type: "slack",
    name: "Slack",
    description: "Team communication and notifications",
    is_connected: false,
    status: "disconnected" as const
  },
  {
    id: "4",
    type: "salesforce",
    name: "Salesforce",
    description: "Customer relationship management",
    is_connected: true,
    connected_at: "2024-01-10T14:30:00Z",
    status: "connected" as const
  },
  {
    id: "5",
    type: "stripe",
    name: "Stripe",
    description: "Payment processing and subscriptions",
    is_connected: false,
    status: "disconnected" as const
  },
  {
    id: "6",
    type: "shopify",
    name: "Shopify",
    description: "E-commerce platform integration",
    is_connected: false,
    status: "disconnected" as const
  }
]

// Helper function to convert hex to rgba
const hexToRgba = (hex: string, alpha: number = 1) => {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

// Preset gradient combinations
const gradientPresets = [
  { name: "Ocean", from: "#3b82f6", to: "#06b6d4", preview: "from-blue-500 to-cyan-500" },
  { name: "Sunset", from: "#f97316", to: "#ec4899", preview: "from-orange-500 to-pink-500" },
  { name: "Forest", from: "#10b981", to: "#84cc16", preview: "from-emerald-500 to-lime-500" },
  { name: "Royal", from: "#8b5cf6", to: "#6366f1", preview: "from-violet-500 to-indigo-500" },
  { name: "Fire", from: "#ef4444", to: "#f97316", preview: "from-red-500 to-orange-500" },
  { name: "Aurora", from: "#06b6d4", to: "#8b5cf6", preview: "from-cyan-500 to-violet-500" },
  { name: "Mint", from: "#10b981", to: "#06b6d4", preview: "from-emerald-500 to-cyan-500" },
  { name: "Berry", from: "#ec4899", to: "#8b5cf6", preview: "from-pink-500 to-violet-500" }
]

export default function EmbedsPage({ params }: EmbedsPageProps) {
  const { partnerId } = use(params)
  const [integrations, setIntegrations] = useState(mockIntegrations)
  const [loading, setLoading] = useState(false)
  const [selectedTheme, setSelectedTheme] = useState<"light" | "dark">("light")
  const [deviceView, setDeviceView] = useState<"desktop" | "mobile">("desktop")
  const [backgroundStyle, setBackgroundStyle] = useState<"white" | "custom">("white")
  const [customGradientFrom, setCustomGradientFrom] = useState("#3b82f6") // blue-500
  const [customGradientTo, setCustomGradientTo] = useState("#8b5cf6") // violet-500
  const [disconnectDialogOpen, setDisconnectDialogOpen] = useState(false)
  const [integrationToDisconnect, setIntegrationToDisconnect] = useState<string | null>(null)
  const [backgroundDialogOpen, setBackgroundDialogOpen] = useState(false)
  const [tempBackgroundStyle, setTempBackgroundStyle] = useState<"white" | "custom">("white")
  const [tempGradientFrom, setTempGradientFrom] = useState("#3b82f6")
  const [tempGradientTo, setTempGradientTo] = useState("#8b5cf6")

  const handleConnect = async (integrationType: string) => {
    try {
      toast.info(`Opening ${integrationType} authorization...`)
      
      // Simulate OAuth flow
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // Update integration status
      setIntegrations(prev => prev.map(integration => 
        integration.type === integrationType
          ? { ...integration, is_connected: true, connected_at: new Date().toISOString(), status: "connected" as const }
          : integration
      ))
      
      toast.success(`Successfully connected ${integrationType}!`)
    } catch (error) {
      toast.error(`Failed to connect ${integrationType}`)
    }
  }

  const handleDisconnect = async (integrationId: string) => {
    setIntegrationToDisconnect(integrationId)
    setDisconnectDialogOpen(true)
  }

  const confirmDisconnect = async () => {
    if (!integrationToDisconnect) return
    
    const integration = integrations.find(i => i.id === integrationToDisconnect)
    
    try {
      setLoading(true)
      await new Promise(resolve => setTimeout(resolve, 500))
      
      setIntegrations(prev => prev.map(i => 
        i.id === integrationToDisconnect
          ? { ...i, is_connected: false, connected_at: undefined, status: "disconnected" as const }
          : i
      ))
      
      toast.success(`${integration?.name} disconnected successfully`)
    } catch (error) {
      toast.error('Failed to disconnect integration')
    } finally {
      setLoading(false)
      setDisconnectDialogOpen(false)
      setIntegrationToDisconnect(null)
    }
  }

  const handleSettings = (integrationId: string) => {
    const integration = integrations.find(i => i.id === integrationId)
    toast.info(`Opening settings for ${integration?.name}...`)
  }

  const handleRefresh = async (integrationId: string) => {
    const integration = integrations.find(i => i.id === integrationId)
    try {
      toast.info(`Refreshing ${integration?.name}...`)
      await new Promise(resolve => setTimeout(resolve, 1000))
      toast.success('Integration refreshed')
    } catch (error) {
      toast.error('Refresh failed')
    }
  }

  const openBackgroundDialog = () => {
    // Set temp values to current values
    setTempBackgroundStyle(backgroundStyle)
    setTempGradientFrom(customGradientFrom)
    setTempGradientTo(customGradientTo)
    setBackgroundDialogOpen(true)
  }

  const applyBackgroundChanges = () => {
    // Apply the temporary selections
    setBackgroundStyle(tempBackgroundStyle)
    setCustomGradientFrom(tempGradientFrom)
    setCustomGradientTo(tempGradientTo)
    setBackgroundDialogOpen(false)
  }

  const copyEmbedCode = (type: "iframe" | "react" | "webcomponent") => {
    let code = ""
    const bgParams = backgroundStyle === "custom" 
      ? `&bg_from=${encodeURIComponent(customGradientFrom)}&bg_to=${encodeURIComponent(customGradientTo)}`
      : ""
    
    switch (type) {
      case "iframe":
        code = `<iframe 
  src="http://localhost:3010/integrations?partner_id=${partnerId}&user_id=USER_ID&theme=${selectedTheme}${bgParams}"
  width="100%"
  height="600"
  frameborder="0">
</iframe>`
        break
      case "react":
        code = `import { ProtoBoxEmbed } from '@protobox/embed-react'

function App() {
  return (
    <ProtoBoxEmbed
      partnerId="${partnerId}"
      userId={currentUser.id}
      theme="${selectedTheme}"${backgroundStyle === "custom" ? `
      backgroundFrom="${customGradientFrom}"
      backgroundTo="${customGradientTo}"` : ""}
      onConnect={(integration) => {
      }}
    />
  )
}`
        break
      case "webcomponent":
        code = `<script src="https://unpkg.com/@protobox/embed-web"></script>

<protobox-embed 
  partner-id="${partnerId}"
  user-id="USER_ID"
  theme="${selectedTheme}"${backgroundStyle === "custom" ? `
  bg-from="${customGradientFrom}"
  bg-to="${customGradientTo}"` : ""}>
</protobox-embed>`
        break
    }
    
    navigator.clipboard.writeText(code)
    toast.success("Embed code copied to clipboard!")
  }

  const deviceWidths = {
    desktop: '100%',
    mobile: '375px'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Integration Embeds</h1>
        <p className="text-muted-foreground">
          Configure and preview your integration marketplace embed
        </p>
      </div>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Embed Configuration</CardTitle>
          <CardDescription>
            Customize the appearance and behavior of your embed
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Theme:</span>
              <Button
                variant={selectedTheme === "light" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedTheme("light")}
              >
                <Sun className="h-4 w-4 mr-2" />
                Light
              </Button>
              <Button
                variant={selectedTheme === "dark" ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedTheme("dark")}
              >
                <Moon className="h-4 w-4 mr-2" />
                Dark
              </Button>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Background:</span>
              <Button
                variant="outline"
                size="sm"
                onClick={openBackgroundDialog}
              >
                <Palette className="h-4 w-4 mr-2" />
                {backgroundStyle === "white" ? "White" : "Gradient"}
              </Button>
              {backgroundStyle === "custom" && (
                <code className="text-xs px-2 py-1 bg-muted rounded">
                  {customGradientFrom} → {customGradientTo}
                </code>
              )}
            </div>
            
            <div className="ml-auto flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(`/partner/${partnerId}/settings/embeds/demo`, '_blank')}
              >
                View Demo
              </Button>
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="outline">
                    <Code className="h-4 w-4 mr-2" />
                    Get Embed Code
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>Embed Code</DialogTitle>
                    <DialogDescription>
                      Choose your preferred implementation method
                    </DialogDescription>
                  </DialogHeader>
                  
                  <Tabs defaultValue="iframe" className="mt-4">
                    <TabsList className="grid w-full grid-cols-3">
                      <TabsTrigger value="iframe">iFrame</TabsTrigger>
                      <TabsTrigger value="react">React</TabsTrigger>
                      <TabsTrigger value="webcomponent">Web Component</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="iframe" className="space-y-4">
                      <div className="relative">
                        <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                          <code>{`<iframe 
  src="http://localhost:3010/integrations?partner_id=${partnerId}&user_id=USER_ID&theme=${selectedTheme}${backgroundStyle === "custom" ? `&bg_from=${encodeURIComponent(customGradientFrom)}&bg_to=${encodeURIComponent(customGradientTo)}` : ""}"
  width="100%"
  height="600"
  frameborder="0">
</iframe>`}</code>
                        </pre>
                        <Button
                          size="sm"
                          variant="secondary"
                          className="absolute top-2 right-2"
                          onClick={() => copyEmbedCode("iframe")}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="react" className="space-y-4">
                      <div className="relative">
                        <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                          <code>{`import { ProtoBoxEmbed } from '@protobox/embed-react'

function App() {
  return (
    <ProtoBoxEmbed
      partnerId="${partnerId}"
      userId={currentUser.id}
      theme="${selectedTheme}"${backgroundStyle === "custom" ? `
      backgroundFrom="${customGradientFrom}"
      backgroundTo="${customGradientTo}"` : ""}
      onConnect={(integration) => {
      }}
    />
  )
}`}</code>
                        </pre>
                        <Button
                          size="sm"
                          variant="secondary"
                          className="absolute top-2 right-2"
                          onClick={() => copyEmbedCode("react")}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </TabsContent>
                    
                    <TabsContent value="webcomponent" className="space-y-4">
                      <div className="relative">
                        <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
                          <code>{`<script src="https://unpkg.com/@protobox/embed-web"></script>

<protobox-embed 
  partner-id="${partnerId}"
  user-id="USER_ID"
  theme="${selectedTheme}"${backgroundStyle === "custom" ? `
  bg-from="${customGradientFrom}"
  bg-to="${customGradientTo}"` : ""}>
</protobox-embed>`}</code>
                        </pre>
                        <Button
                          size="sm"
                          variant="secondary"
                          className="absolute top-2 right-2"
                          onClick={() => copyEmbedCode("webcomponent")}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </TabsContent>
                  </Tabs>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Demo Mode Alert */}
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          <strong>Demo Mode:</strong> OAuth flows are simulated. In production, clicking "Connect" would open the actual OAuth provider's authorization page.
        </AlertDescription>
      </Alert>

      {/* Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Live Preview</span>
            <div className="flex gap-2">
              <Button
                variant={deviceView === "desktop" ? "default" : "outline"}
                size="sm"
                onClick={() => setDeviceView("desktop")}
              >
                <Monitor className="h-4 w-4" />
              </Button>
              <Button
                variant={deviceView === "mobile" ? "default" : "outline"}
                size="sm"
                onClick={() => setDeviceView("mobile")}
              >
                <Smartphone className="h-4 w-4" />
              </Button>
            </div>
          </CardTitle>
          <CardDescription>
            This is how your integration marketplace will appear to users
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex justify-center">
            <div 
              className={`border rounded-lg p-6 transition-all duration-300 ${
                selectedTheme === "dark" 
                  ? "bg-gray-900" 
                  : backgroundStyle === "white" 
                    ? "bg-white" 
                    : ""
              } ${
                deviceView === "mobile" ? "max-w-[375px]" : ""
              }`}
              style={{ 
                width: deviceWidths[deviceView],
                ...(backgroundStyle === "custom" && selectedTheme !== "dark" ? {
                  background: `linear-gradient(to bottom right, ${hexToRgba(customGradientFrom, 0.1)}, ${hexToRgba(customGradientTo, 0.1)})`
                } : {})
              }}
            >
              <ProtoBoxIntegrations
                integrations={integrations}
                loading={loading}
                onConnect={handleConnect}
                onDisconnect={handleDisconnect}
                onSettings={handleSettings}
                onRefresh={handleRefresh}
                className="animate-in fade-in duration-500"
              />
              
              <div className="mt-6 text-center">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Powered by{" "}
                  <a 
                    href="https://github.com/chanl-ai/protobox-python" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="font-medium text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    ProtoBox
                  </a>
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{integrations.length}</div>
            <p className="text-xs text-muted-foreground">Total Integrations</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">
              {integrations.filter(i => i.is_connected).length}
            </div>
            <p className="text-xs text-muted-foreground">Connected</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">Demo</div>
            <p className="text-xs text-muted-foreground">Data Mode</p>
          </CardContent>
        </Card>
      </div>

      <Toaster 
        position="bottom-right"
        toastOptions={{
          style: {
            background: selectedTheme === "dark" ? '#1e293b' : '#fff',
            color: selectedTheme === "dark" ? '#f1f5f9' : '#0f172a',
            border: `1px solid ${selectedTheme === "dark" ? '#334155' : '#e2e8f0'}`
          }
        }}
      />

      {/* Disconnect Confirmation Dialog */}
      <AlertDialog open={disconnectDialogOpen} onOpenChange={setDisconnectDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Disconnect Integration</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to disconnect {integrations.find(i => i.id === integrationToDisconnect)?.name}? 
              This action cannot be undone and you'll need to reconnect and reconfigure the integration.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setIntegrationToDisconnect(null)}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction onClick={confirmDisconnect} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
              Disconnect
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Background Style Dialog */}
      <Dialog open={backgroundDialogOpen} onOpenChange={setBackgroundDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Choose Background Style</DialogTitle>
            <DialogDescription>
              Select a background style for your integration embed
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Background Options */}
            <div className="space-y-3">
              <div 
                className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                  tempBackgroundStyle === "white" ? "border-primary bg-primary/5" : "border-border hover:border-muted-foreground"
                }`}
                onClick={() => setTempBackgroundStyle("white")}
              >
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded border bg-white" />
                  <div>
                    <h4 className="font-medium">White Background</h4>
                    <p className="text-sm text-muted-foreground">Clean, simple white background</p>
                  </div>
                </div>
              </div>

              <div 
                className={`border-2 rounded-lg p-4 cursor-pointer transition-all ${
                  tempBackgroundStyle === "custom" ? "border-primary bg-primary/5" : "border-border hover:border-muted-foreground"
                }`}
                onClick={() => setTempBackgroundStyle("custom")}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded border bg-gradient-to-br ${
                    tempBackgroundStyle === "custom" 
                      ? `from-[${tempGradientFrom}] to-[${tempGradientTo}]`
                      : "from-blue-500 to-violet-500"
                  }`} style={{
                    background: `linear-gradient(to bottom right, ${tempGradientFrom}, ${tempGradientTo})`
                  }} />
                  <div className="flex-1">
                    <h4 className="font-medium">Gradient Background</h4>
                    <p className="text-sm text-muted-foreground">Colorful gradient background</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Gradient Options - Only show when custom is selected */}
            {tempBackgroundStyle === "custom" && (
              <div className="space-y-4 pt-4 border-t">
                <h4 className="text-sm font-semibold">Choose Gradient Colors</h4>
                
                {/* Preset Gradients */}
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Quick presets:</p>
                  <div className="grid grid-cols-4 gap-2">
                    {gradientPresets.map((preset) => (
                      <button
                        key={preset.name}
                        onClick={() => {
                          setTempGradientFrom(preset.from)
                          setTempGradientTo(preset.to)
                        }}
                        className="flex flex-col items-center gap-1 p-2 rounded-md hover:bg-muted transition-colors"
                      >
                        <div className={`w-full h-12 rounded bg-gradient-to-br ${preset.preview}`} />
                        <span className="text-xs">{preset.name}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Custom Color Pickers */}
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Or choose custom colors:</p>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <label className="text-sm font-medium">From:</label>
                      <input
                        type="color"
                        value={tempGradientFrom}
                        onChange={(e) => setTempGradientFrom(e.target.value)}
                        className="h-10 w-20 rounded border cursor-pointer"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="text-sm font-medium">To:</label>
                      <input
                        type="color"
                        value={tempGradientTo}
                        onChange={(e) => setTempGradientTo(e.target.value)}
                        className="h-10 w-20 rounded border cursor-pointer"
                      />
                    </div>
                    <code className="text-sm px-2 py-1 bg-muted rounded ml-auto">
                      {tempGradientFrom} → {tempGradientTo}
                    </code>
                  </div>
                </div>

                {/* Preview */}
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Preview:</p>
                  <div 
                    className="w-full h-24 rounded-lg border"
                    style={{
                      background: `linear-gradient(to bottom right, ${hexToRgba(tempGradientFrom, 0.1)}, ${hexToRgba(tempGradientTo, 0.1)})`
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setBackgroundDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button onClick={applyBackgroundChanges}>
              Apply Changes
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}