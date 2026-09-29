"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ArrowUp, Square, Paperclip } from "lucide-react"
import { cn } from "@/lib/utils"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  created_at: string
  tool_calls?: any[]
}

interface MultimodalInputProps {
  input: string
  setInput: (value: string) => void
  handleSubmit: (content: string) => void
  isLoading: boolean
  stop: () => void
  messages: Message[]
}

export function MultimodalInput({
  input,
  setInput,
  handleSubmit,
  isLoading,
  stop,
  messages,
}: MultimodalInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [attachments, setAttachments] = useState<File[]>([])

  // Auto-resize textarea
  const adjustHeight = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
    }
  }

  useEffect(() => {
    adjustHeight()
  }, [input])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isLoading && input.trim()) {
        handleSubmit(input)
      }
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    setAttachments(prev => [...prev, ...files])
  }

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index))
  }

  const onSubmit = () => {
    if (!isLoading && input.trim()) {
      handleSubmit(input)
    }
  }

  return (
    <div className="border-t bg-background">
      <div className="mx-auto max-w-3xl px-4 py-6">
        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="mb-4 flex flex-wrap gap-2">
            {attachments.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-2 rounded-lg border bg-muted px-3 py-2 text-sm"
              >
                <span className="truncate max-w-40">{file.name}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-4 w-4 p-0"
                  onClick={() => removeAttachment(index)}
                >
                  ×
                </Button>
              </div>
            ))}
          </div>
        )}

        <div className="relative">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Send a message..."
            className={cn(
              "min-h-[48px] max-h-[200px] resize-none rounded-2xl border-0 bg-muted pr-20 pl-12 py-3 text-sm",
              "focus-visible:ring-1 focus-visible:ring-ring",
              "placeholder:text-muted-foreground"
            )}
            disabled={isLoading}
          />

          {/* Attachment button */}
          <div className="absolute left-3 bottom-3">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0"
              disabled={isLoading}
              asChild
            >
              <label>
                <Paperclip className="h-4 w-4" />
                <input
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleFileUpload}
                  accept="image/*,.pdf,.doc,.docx,.txt"
                />
              </label>
            </Button>
          </div>

          {/* Send/Stop button */}
          <div className="absolute right-3 bottom-3">
            {isLoading ? (
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
                onClick={stop}
              >
                <Square className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                className={cn(
                  "h-8 w-8 p-0",
                  input.trim() && "bg-primary text-primary-foreground hover:bg-primary/90"
                )}
                onClick={onSubmit}
                disabled={!input.trim()}
              >
                <ArrowUp className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Suggested actions for empty chat */}
        {messages.length === 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInput("Help me set up a new REST API action")}
            >
              Set up REST API
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInput("Show me my current workspace configuration")}
            >
              View workspace
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setInput("How do I test my integrations?")}
            >
              Test integrations
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}