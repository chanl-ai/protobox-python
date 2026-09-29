"use client"

import { cn } from "@/lib/utils"
import { Loader2, Wrench } from "lucide-react"

interface ToolThinkingProps {
  toolName?: string
  message?: string
  className?: string
}

export function ToolThinking({ toolName, message, className }: ToolThinkingProps) {
  return (
    <div className={cn(
      "inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-muted/50 text-sm",
      className
    )}>
      <div className="flex items-center gap-1.5">
        <Wrench className="h-3.5 w-3.5 text-muted-foreground" />
        <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
      </div>
      <span className="text-muted-foreground">
        {message || (toolName ? `Using ${toolName}...` : "Using tool...")}
      </span>
    </div>
  )
}

// Advanced thinking component with pulsing dots
export function ToolThinkingAdvanced({ 
  toolName, 
  stage,
  className 
}: { 
  toolName?: string
  stage?: "preparing" | "executing" | "processing"
  className?: string 
}) {
  const stageMessages = {
    preparing: "Preparing tool",
    executing: "Executing",
    processing: "Processing results"
  }
  
  return (
    <div className={cn(
      "flex items-center gap-3 px-4 py-3 rounded-lg bg-muted/30 border border-muted",
      className
    )}>
      <div className="relative">
        <Wrench className="h-4 w-4 text-muted-foreground" />
        <div className="absolute -bottom-1 -right-1">
          <Loader2 className="h-3 w-3 animate-spin text-primary" />
        </div>
      </div>
      
      <div className="flex-1">
        <div className="flex items-center gap-2">
          {toolName && (
            <span className="text-sm font-medium">{toolName}</span>
          )}
          {stage && (
            <span className="text-xs text-muted-foreground">
              {stageMessages[stage]}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-1 mt-1">
          <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-pulse" />
          <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-pulse [animation-delay:0.2s]" />
          <div className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-pulse [animation-delay:0.4s]" />
        </div>
      </div>
    </div>
  )
}