"use client"

import { useState, useEffect, useRef } from "react"
import { useChat } from "ai/react"
import { useWorkspaceReady } from "@/hooks"
import { useDefaultAssistant, useThreads, useMessages, useCreateThread, type Assistant, type Thread, type Message } from "@/lib/api/hooks"
import { protoboxClient } from "@/lib/api/protobox-client"
import { tokenManager } from "@/lib/auth/token-manager"
import { toast } from "sonner"
import { EmptyScreen } from "@/components/empty-screen"
import { ChatInput } from "@/components/chat-input-new"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Messages } from "@/components/messages-simple"
import { ChatHeaderWithDrawer } from "@/components/chat-header-with-drawer"
import { Button } from "@/components/ui/button"
import { Plus, MessageSquare, X } from "lucide-react"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
  tool_calls?: any[]
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

export default function ChatPlaygroundPage() {
  const { workspaceId, isReady, user } = useWorkspaceReady()
  
  // Use hooks for assistant and threads
  const { data: assistant, isLoading: assistantLoading } = useDefaultAssistant(workspaceId || undefined)
  const createThreadMutation = useCreateThread()
  
  const [currentThread, setCurrentThread] = useState<Thread | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [hasMoreMessages, setHasMoreMessages] = useState(false)
  const [loadingMoreMessages, setLoadingMoreMessages] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  
  // Load threads when assistant is available
  const { data: threads = [], refetch: refetchThreads } = useThreads(workspaceId || undefined, assistant?.id || '')
  
  // Get auth token for useChat
  const [authToken, setAuthToken] = useState<string>('')
  useEffect(() => {
    const token = tokenManager.getToken()
    if (token) setAuthToken(token)
  }, [])
  
  // Use Vercel AI SDK's useChat hook
  const { messages, input, setInput, handleSubmit, isLoading, setMessages } = useChat({
    api: '/api/chat',
    headers: {
      'Authorization': authToken ? `Bearer ${authToken}` : '',
    },
    body: {
      workspaceId,
      threadId: currentThread?.id,
      assistantId: assistant?.id,
    },
    streamProtocol: 'text',
    onError: (error) => {
      toast.error('Failed to send message')
    },
    onFinish: async () => {
      // Update thread title if this is the first user message
      if (currentThread && messages.length <= 2) {
        // Find the first user message
        const firstUserMessage = messages.find(m => m.role === 'user')
        if (firstUserMessage) {
          const newTitle = firstUserMessage.content.substring(0, 50) + 
            (firstUserMessage.content.length > 50 ? '...' : '')
          
          // Update local state
          const updatedThread = {
            ...currentThread,
            metadata: {
              ...currentThread.metadata,
              title: newTitle
            }
          }
          setCurrentThread(updatedThread)
          setThreads(prev => prev.map(t => 
            t.id === currentThread.id ? updatedThread : t
          ))
        }
      }
    },
  })


  // Function to scroll to bottom
  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]')
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }

  // Auto-scroll to bottom when messages change (but not during load more)
  useEffect(() => {
    if (!loadingMoreMessages) {
      // Small delay to ensure DOM is updated
      setTimeout(scrollToBottom, 100)
    }
  }, [messages, loadingMoreMessages])

  // Initialize chat when assistant and threads are loaded
  useEffect(() => {
    if (!assistant || threads.length === 0) return
    
    // Resume last conversation or create new one
    if (threads.length > 0) {
      // Resume the most recent thread (first in list, sorted by created_at desc)
      const lastThread = threads[0]
      setCurrentThread(lastThread)
    } else {
      // No existing threads - create first conversation
      if (workspaceId && assistant.id) {
        createThreadMutation.mutate({
          workspaceId,
          assistantId: assistant.id,
          data: { 
            title: "New conversation",
            metadata: {} 
          }
        }, {
          onSuccess: (newThread) => {
            setCurrentThread(newThread)
            refetchThreads()
          }
        })
      }
    }
  }, [assistant, threads, workspaceId, createThreadMutation, refetchThreads])
  
  // Load messages when thread is selected
  const { data: messagesData = [] } = useMessages(workspaceId || undefined, currentThread?.id || '', 20)
  
  useEffect(() => {
    if (messagesData.length > 0 && currentThread) {
      const aiMessages = messagesData.map((msg: Message) => ({
        id: msg.id,
        role: msg.role as "user" | "assistant",
        content: msg.content,
      }))
      setMessages(aiMessages)
      setHasMoreMessages(messagesData.length === 20)
    }
  }, [messagesData, currentThread, setMessages])

  // Auto-scroll when messages change
  useEffect(() => {
    // Ensure scroll after message is added
    setTimeout(scrollToBottom, 100)
  }, [messages])

  if (!user) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-lg font-medium mb-2">Authentication Required</div>
          <div className="text-muted-foreground">Please sign in to continue</div>
        </div>
      </div>
    )
  }

  const handleSelectThread = async (threadId: string) => {
    if (!assistant) return
    
    // Find the selected thread
    const selectedThread = threads.find(t => t.id === threadId)
    if (selectedThread) {
      setCurrentThread(selectedThread)
    }
  }

  const handleLoadMoreMessages = async () => {
    if (!currentThread || loadingMoreMessages || !workspaceId) return
    
    setLoadingMoreMessages(true)
    try {
      // Load more messages by increasing the limit
      const newLimit = messages.length + 20
      const response = await protoboxClient.getMessages(workspaceId, currentThread.id, newLimit)
      
      if (response.data) {
        // Convert to Vercel AI SDK format
        const aiMessages = (response.data as Message[]).map((msg: Message) => ({
          id: msg.id,
          role: msg.role as "user" | "assistant",
          content: msg.content,
        }))
        setMessages(aiMessages)
        // Check if we got the expected number of new messages
        setHasMoreMessages(response.data.length === newLimit)
      }
    } catch (error) {
      toast.error('Failed to load more messages')
    } finally {
      setLoadingMoreMessages(false)
    }
  }

  const handleNewChat = async () => {
    if (!assistant || !workspaceId) return
    
    try {
      // Create new thread
      const threadResponse = await assistantsApi.createThread(
        workspaceId,
        assistant.id,
        { 
          title: "New conversation",
          metadata: {} 
        }
      )
      
      if (threadResponse.data) {
        setCurrentThread(threadResponse.data)
        setThreads(prev => [threadResponse.data, ...prev])
        setMessages([])
        setHasMoreMessages(false)
      }
    } catch (error) {
      toast.error('Failed to create new conversation')
    }
  }


  const hasMessages = messages.length > 0

  return (
    <div className="flex h-[calc(100vh-3rem)] bg-background -m-8 md:-my-6 md:-mx-8 relative">
      {/* Sidebar - absolute on mobile, relative on desktop */}
      {sidebarOpen && (
        <>
          {/* Mobile backdrop */}
          <div 
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
          
          <div className="absolute lg:relative w-80 lg:w-80 border-r bg-background flex flex-col z-50 lg:z-auto h-full">
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="font-semibold">Chat History</h2>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0 lg:hidden"
                onClick={() => setSidebarOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            
            <div className="p-4">
              <Button 
                onClick={() => {
                  handleNewChat()
                  setSidebarOpen(false)
                }}
                className="w-full gap-2"
              >
                <Plus className="h-4 w-4" />
                New Chat
              </Button>
            </div>

            <ScrollArea className="flex-1 px-4">
              <div className="space-y-2 pb-4">
                {threads.map((thread) => (
                  <Button
                    key={thread.id}
                    variant={currentThread?.id === thread.id ? "secondary" : "ghost"}
                    className="w-full justify-start text-left h-auto p-3"
                    onClick={() => {
                      handleSelectThread(thread.id)
                      setSidebarOpen(false)
                    }}
                  >
                    <div className="flex items-start gap-2 w-full">
                      <MessageSquare className="h-4 w-4 mt-0.5 shrink-0" />
                      <div className="flex flex-col items-start gap-1 min-w-0 flex-1">
                        <div className="font-medium text-sm truncate w-full">
                          {thread.metadata?.title || 
                           (thread.metadata?.last_message ? thread.metadata.last_message.substring(0, 30) + "..." : "New conversation")}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {new Date(thread.created_at).toLocaleDateString([], { 
                            month: 'short', 
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </div>
                      </div>
                    </div>
                  </Button>
                ))}
                
                {threads.length === 0 && (
                  <div className="text-center text-muted-foreground text-sm py-8">
                    No previous conversations
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        </>
      )}

      {/* Main Chat Container */}
      <div className="flex flex-col min-w-0 flex-1">
        {/* Chat Header */}
        <ChatHeaderWithDrawer
          threads={threads}
          currentThread={currentThread}
          onSelectThread={handleSelectThread}
          onNewChat={handleNewChat}
          hasMessages={hasMessages}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        />

        {/* Messages Area */}
        <div className="flex-1 overflow-hidden">
          {hasMessages ? (
            <ScrollArea ref={scrollAreaRef} className="h-full">
              <div className="flex flex-col min-w-0 gap-6 pt-4 pb-4 relative max-w-4xl mx-auto px-4">
                {/* Load More Button */}
                {hasMoreMessages && (
                  <div className="flex justify-center py-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleLoadMoreMessages}
                      disabled={loadingMoreMessages}
                      className="text-sm"
                    >
                      {loadingMoreMessages ? "Loading..." : "Load previous messages"}
                    </Button>
                  </div>
                )}
                
                <Messages messages={messages.map(msg => {
                  // Extract content from parts if available (Vercel AI SDK v4)
                  let content = msg.content || ''
                  if (!content && msg.parts && msg.parts.length > 0) {
                    content = msg.parts.map((part: any) => 
                      part.text || part.content || part.value || ''
                    ).join('')
                  }
                  
                  return {
                    id: msg.id,
                    role: msg.role as "user" | "assistant",
                    content: content,
                    created_at: new Date().toISOString(),
                  }
                })} isLoading={isLoading} />
                <div className="shrink-0 min-w-[24px] min-h-[24px]"></div>
              </div>
            </ScrollArea>
          ) : (
            <div className="flex flex-col min-w-0 flex-1 overflow-hidden pt-4 relative">
              <EmptyScreen />
            </div>
          )}
        </div>

        {/* Input Form */}
        <div className="relative z-10 bg-background pt-4 pb-6 chat-footer">
          <ChatInput 
            input={input}
            setInput={setInput}
            onSubmit={(message) => {
              // Create a synthetic form event for handleSubmit
              const syntheticEvent = {
                preventDefault: () => {},
              } as React.FormEvent
              
              // Set the input to the message and submit
              setInput(message)
              handleSubmit(syntheticEvent)
            }}
            isLoading={isLoading}
            hasMessages={hasMessages}
          />
        </div>
      </div>
    </div>
  )
}