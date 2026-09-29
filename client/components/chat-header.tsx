"use client"

import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Plus, ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

interface Thread {
  id: string
  assistant_id: string
  created_at: string
  metadata?: {
    title?: string
    last_message?: string
  }
}

interface ChatHeaderProps {
  chatModel: string
  setChatModel: (model: string) => void
  visibilityType: "private" | "public"
  setVisibilityType: (type: "private" | "public") => void
  isReadonly: boolean
  threads: Thread[]
  currentThread: Thread | null
  onNewChat: () => void
  onSelectThread: (threadId: string) => void
}

const chatModels = [
  { id: "gpt-4-turbo-preview", name: "GPT-4 Turbo" },
  { id: "gpt-4", name: "GPT-4" },
  { id: "gpt-3.5-turbo", name: "GPT-3.5 Turbo" },
]

export function ChatHeader({
  chatModel,
  setChatModel,
  visibilityType,
  setVisibilityType,
  isReadonly,
  threads,
  currentThread,
  onNewChat,
  onSelectThread,
}: ChatHeaderProps) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onNewChat}
          className="gap-2"
          disabled={isReadonly}
        >
          <Plus className="h-4 w-4" />
          New Chat
        </Button>

        {threads.length > 0 && (
          <Select
            value={currentThread?.id || ""}
            onValueChange={onSelectThread}
          >
            <SelectTrigger className="w-48">
              <SelectValue placeholder="Select conversation">
                {currentThread?.metadata?.title || 
                 currentThread?.metadata?.last_message?.substring(0, 30) + "..." ||
                 "New conversation"}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {threads.map((thread) => (
                <SelectItem key={thread.id} value={thread.id}>
                  {thread.metadata?.title || 
                   thread.metadata?.last_message?.substring(0, 40) + "..." ||
                   "New conversation"}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      <div className="flex items-center gap-2">
        <Select value={chatModel} onValueChange={setChatModel}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {chatModels.map((model) => (
              <SelectItem key={model.id} value={model.id}>
                {model.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={visibilityType} onValueChange={setVisibilityType}>
          <SelectTrigger className="w-24">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="private">Private</SelectItem>
            <SelectItem value="public">Public</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}