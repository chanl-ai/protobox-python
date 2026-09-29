"use client"

import { memo } from "react"
import { Message } from "@/components/message"

interface MessageType {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
  tool_calls?: any[]
}

interface MessagesProps {
  messages: MessageType[]
  isLoading: boolean
}

function PureMessages({ messages, isLoading }: MessagesProps) {
  return (
    <div className="mx-auto w-full lg:max-w-[700px] px-4">
      <div className="flex flex-col gap-6 pb-4">
        {messages.map((message, index) => (
          <Message
            key={message.id}
            message={message}
            isLoading={isLoading && index === messages.length - 1 && message.role === 'assistant' && !message.content}
          />
        ))}
        
        {/* Show loading indicator when we're loading but haven't received any assistant message yet */}
        {isLoading && !messages.some((msg, index) => 
          index === messages.length - 1 && msg.role === 'assistant'
        ) && (
          <Message
            message={{
              id: 'thinking',
              role: 'assistant',
              content: '',
              created_at: new Date().toISOString()
            }}
            isLoading={true}
          />
        )}
      </div>
    </div>
  )
}

export const Messages = memo(PureMessages, (prevProps, nextProps) => {
  return (
    prevProps.messages.length === nextProps.messages.length &&
    prevProps.isLoading === nextProps.isLoading &&
    prevProps.messages.every((msg, i) => 
      msg.id === nextProps.messages[i]?.id &&
      msg.content === nextProps.messages[i]?.content
    )
  )
})