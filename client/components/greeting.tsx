"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Bot } from "lucide-react"

export function Greeting() {
  return (
    <div className="text-center max-w-md">
      <div className="flex justify-center mb-6">
        <Avatar className="h-16 w-16">
          <AvatarFallback className="bg-primary">
            <Bot className="h-8 w-8 text-primary-foreground" />
          </AvatarFallback>
        </Avatar>
      </div>
      
      <div className="text-2xl font-semibold mb-2">
        Welcome to ProtoBox AI
      </div>
      
      <div className="text-muted-foreground mb-6">
        I'm your AI assistant for MCP server configuration and workspace management. 
        Start a new conversation to begin.
      </div>

      <div className="grid grid-cols-1 gap-3 text-sm">
        <div className="p-3 rounded-lg border bg-muted/50">
          <div className="font-medium mb-1">💡 Configure Actions</div>
          <div className="text-muted-foreground">Set up REST API calls and integrations</div>
        </div>
        
        <div className="p-3 rounded-lg border bg-muted/50">
          <div className="font-medium mb-1">🔧 Manage Workspace</div>
          <div className="text-muted-foreground">Organize your MCP server settings</div>
        </div>
        
        <div className="p-3 rounded-lg border bg-muted/50">
          <div className="font-medium mb-1">🚀 Test Integrations</div>
          <div className="text-muted-foreground">Validate your API connections</div>
        </div>
      </div>
    </div>
  )
}