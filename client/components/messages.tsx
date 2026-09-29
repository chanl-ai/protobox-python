"use client"

import { memo } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { PreviewMessage } from "@/components/preview-message"
import { ThinkingMessage } from "@/components/thinking-message"
import { Greeting } from "@/components/greeting"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
  tool_calls?: any[]
}

interface Thread {
  id: string
  assistant_id: string
  created_at: string
  metadata?: {
    title?: string
    last_message?: string
  }
}

interface MessagesProps {
  messages: Message[]
  isLoading: boolean
  currentThread: Thread | null
}

function MessagesComponent({ messages, isLoading, currentThread }: MessagesProps) {
  if (!currentThread) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <Greeting />
      </div>
    )
  }

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <div className="text-center max-w-md">
          <div className="text-2xl font-semibold mb-2">What can I help you with?</div>
          <div className="text-muted-foreground">
            I can help you with your MCP server configuration, actions, and workspace setup.
          </div>
        </div>
      </div>
    )
  }

  return (
    <ScrollArea className="flex-1">
      <div className="mx-auto max-w-3xl px-4">
        <div className="flex flex-col gap-6 pb-4">
          {messages.map((message, index) => (
            <PreviewMessage
              key={message.id}
              message={message}
              isLoading={isLoading && index === messages.length - 1}
            />
          ))}
          
          {isLoading && (
            <ThinkingMessage />
          )}
        </div>
      </div>
    </ScrollArea>
  )
}

export const Messages = memo(MessagesComponent, (prevProps, nextProps) => {
  return (
    prevProps.messages.length === nextProps.messages.length &&
    prevProps.isLoading === nextProps.isLoading &&
    prevProps.currentThread?.id === nextProps.currentThread?.id
  )
})