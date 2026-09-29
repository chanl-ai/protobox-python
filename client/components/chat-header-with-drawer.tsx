"use client"

import { Button } from "@/components/ui/button"
import { Menu, Plus } from "lucide-react"

interface Thread {
  id: string
  assistant_id: string
  created_at: string
  metadata?: {
    title?: string
    last_message?: string
  }
}

interface ChatHeaderWithDrawerProps {
  threads: Thread[]
  currentThread: Thread | null
  onSelectThread: (threadId: string) => void
  onNewChat: () => void
  hasMessages: boolean
  sidebarOpen: boolean
  onToggleSidebar: () => void
}

export function ChatHeaderWithDrawer({
  currentThread,
  onNewChat,
  hasMessages,
  sidebarOpen,
  onToggleSidebar
}: ChatHeaderWithDrawerProps) {
  const getThreadTitle = (thread: Thread) => {
    if (thread.metadata?.title) {
      return thread.metadata.title
    }
    if (thread.metadata?.last_message) {
      return thread.metadata.last_message.substring(0, 30) + "..."
    }
    return "New conversation"
  }

  // Always show header for sidebar access and new chat functionality

  return (
    <div className="bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 w-full">
      <div className="w-full px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-8 w-8 p-0"
              onClick={onToggleSidebar}
            >
              <Menu className="h-4 w-4" />
            </Button>

            <div className="text-sm font-medium truncate">
              {currentThread ? getThreadTitle(currentThread) : "Chat"}
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={onNewChat}
            className="gap-2 hidden sm:inline-flex"
          >
            <Plus className="h-4 w-4" />
            <span className="hidden md:inline">New</span>
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={onNewChat}
            className="h-8 w-8 p-0 sm:hidden"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}