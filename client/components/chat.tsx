"use client"

import { useState, useEffect, useRef } from "react"
import { useAuth } from "@/lib/auth"
import { useWorkspaceReady } from "@/hooks"
import { useDefaultAssistant, useThreads, useMessages, useCreateThread, type Assistant, type Thread, type Message } from "@/lib/api/hooks"
import { protoboxClient } from "@/lib/api/protobox-client"
import { toast } from "sonner"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ChatHeader } from "@/components/chat-header"
import { Messages } from "@/components/messages"
import { MultimodalInput } from "@/components/multimodal-input"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
  tool_calls?: ToolCall[]
}

interface ToolCall {
  id: string
  type: string
  function: {
    name: string
    arguments: string
  }
  status?: "running" | "completed" | "error"
  result?: any
}

interface Assistant {
  id: string
  name: string
  instructions: string
  model: string
  tools: any[]
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

interface Session {
  user: {
    id: string
    email?: string
  }
}

export interface ChatProps {
  id: string
  initialMessages: Message[]
  initialChatModel: string
  initialVisibilityType: "private" | "public"
  isReadonly: boolean
  session: Session
  autoResume: boolean
}

export function Chat({
  id,
  initialMessages,
  initialChatModel,
  initialVisibilityType,
  isReadonly,
  session,
  autoResume,
}: ChatProps) {
  const { workspaceId, isReady } = useWorkspaceReady()
  const { user } = useAuth()
  
  const [assistant, setAssistant] = useState<Assistant | null>(null)
  const [threads, setThreads] = useState<Thread[]>([])
  const [currentThread, setCurrentThread] = useState<Thread | null>(null)
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [visibilityType, setVisibilityType] = useState(initialVisibilityType)
  const [chatModel, setChatModel] = useState(initialChatModel)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Load or create assistant
  useEffect(() => {
    const initializeAssistant = async () => {
      // Auth handled by layout
      if (!isReady || !workspaceId) return
      
      try {
        // Get or create the default assistant for the workspace
        const defaultAssistantResponse = await protoboxClient.getOrCreateDefaultAssistant(workspaceId)
        
        if (defaultAssistantResponse.data) {
          const selectedAssistant = defaultAssistantResponse.data
          setAssistant(selectedAssistant)
          
          // Load threads for this assistant
          const threadsResponse = await protoboxClient.listThreads(
            workspaceId, 
            selectedAssistant.id
          )
          if (threadsResponse.data) {
            setThreads(threadsResponse.data)
            
            // Auto-resume with first thread if requested
            if (autoResume && threadsResponse.data.length > 0) {
              setCurrentThread(threadsResponse.data[0])
            }
          }
        } else {
          throw new Error('Failed to get default assistant')
        }
      } catch (error) {
        toast.error('Failed to load assistant')
      }
    }

    initializeAssistant()
  }, [isReady, user?.customToken, workspaceId, chatModel, autoResume])

  // Load messages when thread changes
  useEffect(() => {
    const loadMessages = async () => {
      if (!isReady || !currentThread || !user?.customToken || !workspaceId) return
      
      try {
        const messagesResponse = await protoboxClient.getMessages(
          workspaceId,
          currentThread.id
        )
        
        if (messagesResponse.data) {
          setMessages(messagesResponse.data)
        }
      } catch (error) {
        toast.error('Failed to load conversation')
      }
    }

    loadMessages()
  }, [currentThread, isReady, user?.customToken, workspaceId])

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || !currentThread || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: content.trim(),
      created_at: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput("")
    setLoading(true)
    setIsTyping(true)

    try {
      // Send message to the assistant
      const response = await protoboxClient.sendMessage(
        workspaceId,
        currentThread.id,
        { content: userMessage.content }
      )

      if (response.data) {
        // Extract assistant's response from events
        const assistantMessage = response.data.message || response.data
        if (assistantMessage) {
          setMessages(prev => [...prev, {
            id: assistantMessage.id || Date.now().toString(),
            role: "assistant",
            content: assistantMessage.content || "",
            created_at: assistantMessage.created_at || new Date().toISOString(),
            tool_calls: assistantMessage.tool_calls
          }])
          
          // Update thread metadata
          setThreads(prev => prev.map(t => 
            t.id === currentThread.id 
              ? {
                  ...t,
                  metadata: {
                    ...t.metadata,
                    last_message: assistantMessage.content?.substring(0, 100)
                  }
                }
              : t
          ))
        }
      }
    } catch (error) {
      toast.error('Failed to send message')
      
      // Remove the user message on error
      setMessages(prev => prev.filter(m => m.id !== userMessage.id))
    } finally {
      setLoading(false)
      setIsTyping(false)
    }
  }

  const handleNewChat = async () => {
    if (!assistant) return
    
    try {
      const threadResponse = await protoboxClient.createThread(
        workspaceId, 
        assistant.id,
        { 
          title: "New conversation",
          metadata: {} 
        }
      )
      
      if (threadResponse.data) {
        setThreads(prev => [threadResponse.data, ...prev])
        setCurrentThread(threadResponse.data)
        setMessages([])
      }
    } catch (error) {
      toast.error('Failed to create new conversation')
    }
  }

  return (
    <div className="flex flex-col h-full">
      <ChatHeader
        chatModel={chatModel}
        setChatModel={setChatModel}
        visibilityType={visibilityType}
        setVisibilityType={setVisibilityType}
        isReadonly={isReadonly}
        threads={threads}
        currentThread={currentThread}
        onNewChat={handleNewChat}
        onSelectThread={(threadId) => {
          const thread = threads.find(t => t.id === threadId)
          if (thread) setCurrentThread(thread)
        }}
      />
      
      <div className="flex-1 overflow-hidden">
        <Messages
          messages={messages}
          isLoading={isTyping}
          currentThread={currentThread}
        />
      </div>

      {!isReadonly && currentThread && (
        <MultimodalInput
          input={input}
          setInput={setInput}
          handleSubmit={handleSendMessage}
          isLoading={loading}
          stop={() => setLoading(false)}
          messages={messages}
        />
      )}
    </div>
  )
}