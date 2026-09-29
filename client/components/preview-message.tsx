"use client"

import { memo } from "react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { User, Bot, ThumbsUp, ThumbsDown, Copy } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "sonner"
import { ToolCallContainer } from "@/components/tool-call-card"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
  tool_calls?: any[]
}

interface PreviewMessageProps {
  message: Message
  isLoading?: boolean
}

function PreviewMessageComponent({ message, isLoading }: PreviewMessageProps) {
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      toast.success("Copied to clipboard")
    } catch (error) {
      toast.error("Failed to copy")
    }
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className={cn(
      "group relative flex gap-4 px-4 py-6",
      message.role === "user" && "flex-row-reverse"
    )}>
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback>
          {message.role === "user" ? (
            <User className="h-4 w-4" />
          ) : (
            <Bot className="h-4 w-4" />
          )}
        </AvatarFallback>
      </Avatar>

      <div className={cn(
        "flex flex-col gap-2 max-w-[80%]",
        message.role === "user" && "items-end"
      )}>
        <div className={cn(
          "rounded-2xl px-4 py-3 text-sm",
          message.role === "user" 
            ? "bg-primary text-primary-foreground ml-12" 
            : "bg-muted mr-12"
        )}>
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
          
          {message.tool_calls && message.tool_calls.length > 0 && (
            <div className="mt-3">
              <ToolCallContainer 
                toolCalls={message.tool_calls} 
                variant="simple"
                className="mt-2"
              />
            </div>
          )}
        </div>

        <div className={cn(
          "flex items-center gap-1 text-xs text-muted-foreground",
          message.role === "user" && "flex-row-reverse"
        )}>
          <span>{formatTime(message.created_at)}</span>
          
          {message.role === "assistant" && (
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={handleCopy}
              >
                <Copy className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
              >
                <ThumbsUp className="h-3 w-3" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
              >
                <ThumbsDown className="h-3 w-3" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export const PreviewMessage = memo(PreviewMessageComponent)