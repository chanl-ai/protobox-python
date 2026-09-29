"use client"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { User, Bot, Copy, ThumbsUp, ThumbsDown } from "lucide-react"
import { toast } from "sonner"
import { ToolCallContainer } from "@/components/tool-call-card"

interface MessageType {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
  tool_calls?: any[]
}

interface MessageProps {
  message: MessageType
  isLoading?: boolean
}

export function Message({ message, isLoading }: MessageProps) {
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

  // Handle loading state for assistant
  if (isLoading && message.role === "assistant" && !message.content) {
    return (
      <div className="group relative flex items-start gap-4">
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback>
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>

        <div className="flex flex-col gap-2 min-w-0 max-w-[80%]">
          <div className="rounded-2xl px-4 py-3 text-sm bg-muted">
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-pulse" />
                <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-pulse [animation-delay:0.2s]" />
                <div className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-pulse [animation-delay:0.4s]" />
              </div>
              <span className="text-muted-foreground text-xs">Thinking...</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={`group relative flex items-start gap-4 ${
      message.role === "user" ? "flex-row-reverse" : "flex-row"
    }`}>
      <Avatar className="h-8 w-8 shrink-0">
        <AvatarFallback>
          {message.role === "user" ? (
            <User className="h-4 w-4" />
          ) : (
            <Bot className="h-4 w-4" />
          )}
        </AvatarFallback>
      </Avatar>

      <div className={`flex flex-col gap-2 min-w-0 max-w-[80%] ${
        message.role === "user" ? "items-end" : "items-start"
      }`}>
        <div className={`rounded-2xl px-4 py-3 text-sm ${
          message.role === "user"
            ? "bg-primary text-primary-foreground"
            : "bg-muted"
        }`}>
          {/* Message content */}
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>
          
          {/* Tool calls */}
          {message.tool_calls && message.tool_calls.length > 0 && (
            <ToolCallContainer 
              toolCalls={message.tool_calls} 
              variant="medium"
              className="mt-3"
            />
          )}
        </div>

        {/* Message metadata and actions */}
        <div className={`flex items-center gap-2 text-xs text-muted-foreground ${
          message.role === "user" ? "flex-row-reverse" : "flex-row"
        }`}>
          <span>{formatTime(message.created_at)}</span>
          
          {message.role === "assistant" && message.content && (
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