"use client"

import { useState, useEffect } from "react"
import { protoboxClient } from "@/lib/api/protobox-client"
import { useWorkspaceReady } from "@/hooks"
import { MCPToolsTable, type MCPTool } from "./mcp-tools-table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Zap, Settings } from "lucide-react"

interface IntegrationSettingsProps {
  integrationId: string
  integrationName: string
  isConnected: boolean
  onSettingsChange?: (settings: any) => void
  className?: string
  children?: React.ReactNode // For custom advanced settings
}

export function IntegrationSettings({
  integrationId,
  integrationName,
  isConnected,
  onSettingsChange,
  className,
  children
}: IntegrationSettingsProps) {
  const { workspaceId } = useWorkspaceReady()
  const [tools, setTools] = useState<MCPTool[]>([])
  const [toolsLoading, setToolsLoading] = useState(false)
  const [toolsError, setToolsError] = useState<string | null>(null)
  const [enabledTools, setEnabledTools] = useState<Record<string, boolean>>({})
  const [testResult, setTestResult] = useState<{
    success: boolean
    message: string
  } | null>(null)

  // Fetch available tools when component mounts or integration changes
  useEffect(() => {
    if (workspaceId && integrationId && isConnected) {
      fetchTools()
    }
  }, [workspaceId, integrationId, isConnected])

  const fetchTools = async () => {
    if (!workspaceId) return
    
    setToolsLoading(true)
    setToolsError(null)
    
    try {
      const response = await protoboxClient.getIntegrationTools(workspaceId, integrationId)
      if (response.data?.available_tools) {
        const availableTools = response.data.available_tools as MCPTool[]
        setTools(availableTools)
        // Initialize enabled state from fetched data
        const enabledState = availableTools.reduce((acc, tool) => ({
          ...acc,
          [tool.template_id]: tool.enabled
        }), {} as Record<string, boolean>)
        setEnabledTools(enabledState)
      }
    } catch (error) {
      console.error("Failed to fetch tools:", error)
      setToolsError("Failed to load tools")
    } finally {
      setToolsLoading(false)
    }
  }

  const toggleTool = async (toolId: string) => {
    if (!workspaceId || !integrationId) return
    
    const currentState = enabledTools[toolId]
    const newState = !currentState
    
    // Optimistically update UI
    setEnabledTools(prev => ({ ...prev, [toolId]: newState }))
    
    try {
      if (newState) {
        // Enable the tool
        await protoboxClient.enableIntegrationTool(workspaceId, integrationId, toolId)
      } else {
        // Disable the tool
        await protoboxClient.disableIntegrationTool(workspaceId, integrationId, toolId)
      }
      
      // Refresh tools list to get updated state
      await fetchTools()
      
      // Notify parent of changes
      onSettingsChange?.({ tools: { ...enabledTools, [toolId]: newState } })
    } catch (error) {
      // Revert on error
      console.error("Failed to toggle tool:", error)
      setEnabledTools(prev => ({ ...prev, [toolId]: currentState }))
      setTestResult({
        success: false,
        message: `Failed to ${newState ? 'enable' : 'disable'} tool: ${(error as Error).message}`
      })
    }
  }

  return (
    <div className={className}>
      <Tabs defaultValue="tools" className="w-full">
        <TabsList className="grid grid-cols-2">
          <TabsTrigger value="tools" className="gap-2">
            <Zap className="h-4 w-4" />
            MCP Tools
          </TabsTrigger>
          {children && (
            <TabsTrigger value="advanced" className="gap-2">
              <Settings className="h-4 w-4" />
              Advanced Settings
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="tools" className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground mb-4">
              Select which tools AI assistants can use when connected to your MCP server
            </p>
            
            <MCPToolsTable
              tools={tools}
              enabledTools={enabledTools}
              onToggleTool={toggleTool}
              loading={toolsLoading}
              error={toolsError}
            />
          </div>
        </TabsContent>

        {children && (
          <TabsContent value="advanced" className="">
            <div className="pl-6 pr-2 space-y-4">
              {children}
            </div>
          </TabsContent>
        )}
      </Tabs>

      {testResult && (
        <div
          className={`mt-4 rounded-lg p-3 text-sm ${
            testResult.success
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {testResult.message}
        </div>
      )}
    </div>
  )
}