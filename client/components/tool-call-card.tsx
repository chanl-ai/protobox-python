"use client"

import { cn } from "@/lib/utils"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronRight, Loader2, CheckCircle2, XCircle, AlertCircle, Wrench } from "lucide-react"
import { useState } from "react"

interface ToolCall {
  id?: string
  type?: string
  function?: {
    name: string
    arguments?: any
  }
  name?: string
  arguments?: any
  status?: "pending" | "running" | "completed" | "failed"
  result?: any
  error?: any
}

interface ToolCallCardProps {
  toolCall: ToolCall
  className?: string
}

// Simple tool call card - just shows the tool name and status
export function ToolCallCardSimple({ toolCall, className }: ToolCallCardProps) {
  const name = toolCall.function?.name || toolCall.name || "Unknown Tool"
  const status = toolCall.status || "pending"
  
  const statusConfig = {
    pending: { icon: AlertCircle, color: "text-yellow-600", bgColor: "bg-yellow-50" },
    running: { icon: Loader2, color: "text-blue-600", bgColor: "bg-blue-50" },
    completed: { icon: CheckCircle2, color: "text-green-600", bgColor: "bg-green-50" },
    failed: { icon: XCircle, color: "text-red-600", bgColor: "bg-red-50" }
  }
  
  const config = statusConfig[status]
  const Icon = config.icon
  
  return (
    <div className={cn(
      "inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs",
      config.bgColor,
      className
    )}>
      <Wrench className="h-3 w-3 text-muted-foreground" />
      <span className="font-medium">{name}</span>
      <Icon className={cn("h-3 w-3", config.color, status === "running" && "animate-spin")} />
    </div>
  )
}

// Medium complexity card - shows tool info in a compact card
export function ToolCallCardMedium({ toolCall, className }: ToolCallCardProps) {
  const name = toolCall.function?.name || toolCall.name || "Unknown Tool"
  const status = toolCall.status || "pending"
  const args = toolCall.function?.arguments || toolCall.arguments
  
  const statusConfig = {
    pending: { label: "Pending", variant: "secondary" as const },
    running: { label: "Running", variant: "default" as const },
    completed: { label: "Completed", variant: "success" as const },
    failed: { label: "Failed", variant: "destructive" as const }
  }
  
  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardHeader className="pb-3 pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-sm font-medium">{name}</CardTitle>
          </div>
          <Badge variant={statusConfig[status].variant} className="text-xs">
            {statusConfig[status].label}
          </Badge>
        </div>
      </CardHeader>
      {args && (
        <CardContent className="pt-0 pb-3">
          <pre className="text-xs text-muted-foreground overflow-x-auto">
            {JSON.stringify(args, null, 2)}
          </pre>
        </CardContent>
      )}
    </Card>
  )
}

// Full featured card - expandable with results and error handling
export function ToolCallCard({ toolCall, className }: ToolCallCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const name = toolCall.function?.name || toolCall.name || "Unknown Tool"
  const status = toolCall.status || "pending"
  const args = toolCall.function?.arguments || toolCall.arguments
  
  const statusConfig = {
    pending: { 
      label: "Pending", 
      icon: AlertCircle, 
      color: "text-yellow-600",
      bgColor: "bg-yellow-50",
      borderColor: "border-yellow-200"
    },
    running: { 
      label: "Running", 
      icon: Loader2, 
      color: "text-blue-600",
      bgColor: "bg-blue-50",
      borderColor: "border-blue-200"
    },
    completed: { 
      label: "Completed", 
      icon: CheckCircle2, 
      color: "text-green-600",
      bgColor: "bg-green-50",
      borderColor: "border-green-200"
    },
    failed: { 
      label: "Failed", 
      icon: XCircle, 
      color: "text-red-600",
      bgColor: "bg-red-50",
      borderColor: "border-red-200"
    }
  }
  
  const config = statusConfig[status]
  const StatusIcon = config.icon
  
  return (
    <Card className={cn(
      "overflow-hidden transition-all",
      config.borderColor,
      className
    )}>
      <CardHeader 
        className={cn(
          "cursor-pointer select-none",
          config.bgColor
        )}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
              <Wrench className="h-4 w-4 text-muted-foreground" />
            </div>
            <CardTitle className="text-sm font-medium">{name}</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <StatusIcon className={cn(
              "h-4 w-4", 
              config.color,
              status === "running" && "animate-spin"
            )} />
            <span className={cn("text-xs font-medium", config.color)}>
              {config.label}
            </span>
          </div>
        </div>
        {!isExpanded && args && (
          <CardDescription className="mt-1.5 text-xs truncate">
            {typeof args === 'string' ? args : JSON.stringify(args)}
          </CardDescription>
        )}
      </CardHeader>
      
      {isExpanded && (
        <CardContent className="pt-4 space-y-3">
          {args && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-1">Arguments</h4>
              <pre className="text-xs bg-muted p-2 rounded-md overflow-x-auto">
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          )}
          
          {status === "completed" && toolCall.result && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-1">Result</h4>
              <pre className="text-xs bg-muted p-2 rounded-md overflow-x-auto max-h-32 overflow-y-auto">
                {typeof toolCall.result === 'string' 
                  ? toolCall.result 
                  : JSON.stringify(toolCall.result, null, 2)
                }
              </pre>
            </div>
          )}
          
          {status === "failed" && toolCall.error && (
            <div>
              <h4 className="text-xs font-medium text-red-600 mb-1">Error</h4>
              <pre className="text-xs bg-red-50 text-red-600 p-2 rounded-md overflow-x-auto">
                {typeof toolCall.error === 'string' 
                  ? toolCall.error 
                  : JSON.stringify(toolCall.error, null, 2)
                }
              </pre>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}

// Container for multiple tool calls
export function ToolCallContainer({ 
  toolCalls, 
  variant = "medium",
  className 
}: { 
  toolCalls: ToolCall[]
  variant?: "simple" | "medium" | "full"
  className?: string 
}) {
  if (!toolCalls || toolCalls.length === 0) return null
  
  const Component = variant === "simple" ? ToolCallCardSimple : 
                   variant === "medium" ? ToolCallCardMedium : 
                   ToolCallCard
  
  return (
    <div className={cn("space-y-2", className)}>
      {variant === "simple" ? (
        <div className="flex flex-wrap gap-2">
          {toolCalls.map((toolCall, index) => (
            <Component key={toolCall.id || index} toolCall={toolCall} />
          ))}
        </div>
      ) : (
        toolCalls.map((toolCall, index) => (
          <Component key={toolCall.id || index} toolCall={toolCall} />
        ))
      )}
    </div>
  )
}