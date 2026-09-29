"use client"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { MessageSquare, Plus, Trash2 } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

interface Thread {
  id: string
  assistant_id: string
  created_at: string
  metadata?: {
    title?: string
    last_message?: string
  }
}

interface ChatSidebarProps {
  threads: Thread[]
  currentThreadId?: string
  onSelectThread: (threadId: string) => void
  onNewChat: () => void
  onDeleteThread: (threadId: string) => void
  className?: string
}

export function ChatSidebar({
  threads,
  currentThreadId,
  onSelectThread,
  onNewChat,
  onDeleteThread,
  className
}: ChatSidebarProps) {
  return (
    <div className={cn("flex h-full w-80 flex-col border-r bg-muted/10", className)}>
      <div className="flex items-center justify-between p-4">
        <h2 className="text-lg font-semibold">Conversations</h2>
        <Button
          variant="ghost"
          size="icon"
          onClick={onNewChat}
          className="h-8 w-8"
        >
          <Plus className="h-4 w-4" />
          <span className="sr-only">New chat</span>
        </Button>
      </div>
      
      <ScrollArea className="flex-1">
        <div className="space-y-2 p-2">
          {threads.length === 0 ? (
            <div className="p-8 text-center text-sm text-muted-foreground">
              No conversations yet. Start a new chat!
            </div>
          ) : (
            threads.map((thread) => (
              <div
                key={thread.id}
                className={cn(
                  "group relative rounded-lg hover:bg-muted/50",
                  currentThreadId === thread.id && "bg-muted"
                )}
              >
                <button
                  onClick={() => onSelectThread(thread.id)}
                  className="flex w-full flex-col gap-1 rounded-lg p-3 text-left"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-medium line-clamp-1">
                        {thread.metadata?.title || "New conversation"}
                      </span>
                    </div>
                  </div>
                  {thread.metadata?.last_message && (
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {thread.metadata.last_message}
                    </p>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(thread.created_at), { addSuffix: true })}
                  </span>
                </button>
                
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteThread(thread.id)
                  }}
                  className="absolute right-2 top-2 h-6 w-6 opacity-0 group-hover:opacity-100"
                >
                  <Trash2 className="h-3 w-3" />
                  <span className="sr-only">Delete conversation</span>
                </Button>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  )
}