"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Bot } from "lucide-react"
import { ToolThinking } from "@/components/tool-thinking"

interface ThinkingMessageProps {
  isUsingTool?: boolean
  toolName?: string
}

export function ThinkingMessage({ isUsingTool, toolName }: ThinkingMessageProps) {
  return (
    <div className="group relative flex gap-4 px-4 py-6">
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback>
          <Bot className="h-4 w-4" />
        </AvatarFallback>
      </Avatar>

      <div className="flex flex-col gap-2 max-w-[80%]">
        {isUsingTool ? (
          <ToolThinking toolName={toolName} className="mr-12" />
        ) : (
          <div className="rounded-2xl px-4 py-3 text-sm bg-muted mr-12">
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-pulse" />
                <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-pulse [animation-delay:0.2s]" />
                <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-pulse [animation-delay:0.4s]" />
              </div>
              <span className="text-muted-foreground text-xs">Thinking...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}