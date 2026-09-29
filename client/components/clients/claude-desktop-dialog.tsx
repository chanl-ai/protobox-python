"use client"

import { useState, useEffect } from "react"
import { Copy, Check, Download, ChevronRight, AlertCircle, CheckCircle2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Separator } from "@/components/ui/separator"
import { useToast } from "@/hooks/use-toast"
import { useAuthStore } from "@/lib/auth/stores/auth.store"

interface ClaudeDesktopDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ClaudeDesktopDialog({ open, onOpenChange }: ClaudeDesktopDialogProps) {
  const { currentWorkspace } = useAuthStore()
  const { toast } = useToast()
  const [copiedItem, setCopiedItem] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState(1)
  
  // WorkspaceLoadingGuard ensures currentWorkspace exists when used in dashboard
  const workspaceId = currentWorkspace.id
  
  const getMcpBaseUrl = () => {
    if (process.env.NEXT_PUBLIC_MCP_BASE_URL) {
      return process.env.NEXT_PUBLIC_MCP_BASE_URL
    }
    if (process.env.NEXT_PUBLIC_API_URL) {
      return process.env.NEXT_PUBLIC_API_URL
    }
    return process.env.NODE_ENV === 'development' 
      ? 'http://localhost:8090'
      : 'http://localhost:8090'
  }
  
  const handleCopy = async (text: string, itemId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedItem(itemId)
      setTimeout(() => setCopiedItem(null), 2000)
      toast({
        title: "Copied!",
        description: "Configuration copied to clipboard",
      })
    } catch (error) {
      toast({
        title: "Failed to copy",
        description: "Please try again",
        variant: "destructive",
      })
    }
  }

  const handleDownloadDXT = () => {
    // Generate DXT manifest for ProtoBox
    const manifest = {
      "name": "ProtoBox MCP Server",
      "version": "1.0.0",
      "description": `Connect to ${currentWorkspace.name} workspace`,
      "author": "ProtoBox",
      "mcp": {
        "type": "sse",
        "url": `${getMcpBaseUrl()}/mcp/${workspaceId}/sse`,
        "authentication": {
          "type": "bearer",
          "token": "YOUR_MCP_TOKEN" // User needs to replace this
        }
      },
      "configuration": {
        "fields": [
          {
            "name": "token",
            "label": "MCP Token",
            "type": "string",
            "required": true,
            "sensitive": true,
            "description": "Your ProtoBox MCP token from Settings → API"
          }
        ]
      }
    }

    const blob = new Blob([JSON.stringify(manifest, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `protobox-${workspaceId}.dxt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    toast({
      title: "DXT file downloaded!",
      description: "Double-click the file to install in Claude Desktop",
    })
  }

  const steps = [
    {
      number: 1,
      title: "Download Extension",
      description: "Download the ProtoBox DXT extension file",
      action: (
        <Button onClick={handleDownloadDXT} className="w-full">
          <Download className="mr-2 h-4 w-4" />
          Download ProtoBox.dxt
        </Button>
      ),
      help: "This file contains the configuration for connecting Claude Desktop to your ProtoBox workspace"
    },
    {
      number: 2,
      title: "Install in Claude Desktop",
      description: "Double-click the downloaded .dxt file to install",
      action: (
        <div className="space-y-3">
          <div className="rounded-lg bg-muted p-3 text-sm">
            <p className="font-medium mb-2">Alternative installation:</p>
            <ol className="space-y-1 ml-4">
              <li>1. Open Claude Desktop</li>
              <li>2. Go to Settings → Developer → Extensions</li>
              <li>3. Click "Install Extension"</li>
              <li>4. Select the downloaded .dxt file</li>
            </ol>
          </div>
        </div>
      ),
      help: "Claude Desktop will prompt you to confirm the installation"
    },
    {
      number: 3,
      title: "Add Your MCP Token",
      description: "Configure the extension with your ProtoBox token",
      action: (
        <div className="space-y-3">
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              During installation, Claude will ask for your MCP token. 
              Get one from <a href="/dashboard/settings/api" className="text-primary hover:underline">Settings → API</a>
            </AlertDescription>
          </Alert>
          <div className="rounded-lg bg-muted p-3">
            <p className="text-sm text-muted-foreground">
              Your token will be securely stored in your system's keychain
            </p>
          </div>
        </div>
      ),
      help: "The token authenticates Claude Desktop with your ProtoBox workspace"
    },
    {
      number: 4,
      title: "Restart Claude Desktop",
      description: "Restart the app to activate the connection",
      action: (
        <div className="rounded-lg border border-green-500/20 bg-green-50/10 p-4">
          <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-5 w-5" />
            <span className="font-medium">Setup Complete!</span>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            After restarting, your ProtoBox tools will be available in Claude Desktop
          </p>
        </div>
      ),
      help: "You can verify the connection by asking Claude to list available tools"
    }
  ]

  const currentStepData = steps[currentStep - 1]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <img src="/images/claude-logo.svg" alt="" className="h-8 w-8" />
            <div>
              <DialogTitle>Connect Claude Desktop</DialogTitle>
              <DialogDescription>
                Install ProtoBox as a Desktop Extension (DXT) in Claude Desktop
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        
        <div className="mt-6">
          {/* Progress indicator */}
          <div className="flex items-center justify-between mb-8">
            {steps.map((step, index) => (
              <div key={step.number} className="flex items-center">
                <div className={`
                  flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold
                  ${currentStep === step.number 
                    ? 'bg-primary text-primary-foreground' 
                    : currentStep > step.number
                    ? 'bg-green-500 text-white'
                    : 'bg-muted text-muted-foreground'
                  }
                `}>
                  {currentStep > step.number ? <Check className="h-5 w-5" /> : step.number}
                </div>
                {index < steps.length - 1 && (
                  <div className={`
                    mx-2 h-0.5 w-16 transition-colors
                    ${currentStep > step.number ? 'bg-green-500' : 'bg-muted'}
                  `} />
                )}
              </div>
            ))}
          </div>

          {/* Current step content */}
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold mb-2">
                Step {currentStepData.number}: {currentStepData.title}
              </h3>
              <p className="text-muted-foreground">
                {currentStepData.description}
              </p>
            </div>

            {currentStepData.action}

            {currentStepData.help && (
              <div className="flex items-start gap-2 text-sm text-muted-foreground">
                <AlertCircle className="h-4 w-4 mt-0.5" />
                <span>{currentStepData.help}</span>
              </div>
            )}

            <Separator />

            {/* Navigation buttons */}
            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
                disabled={currentStep === 1}
              >
                Previous
              </Button>
              
              {currentStep < steps.length ? (
                <Button
                  onClick={() => setCurrentStep(currentStep + 1)}
                >
                  Next Step
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              ) : (
                <Button
                  variant="default"
                  onClick={() => onOpenChange(false)}
                >
                  Done
                </Button>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}