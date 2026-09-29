"use client"

import { useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { SuggestedActions } from "@/components/suggested-actions"
import { Paperclip, ArrowUp } from "lucide-react"

interface ChatInputProps {
  input: string
  setInput: (value: string) => void
  onSubmit: (message: string) => void
  isLoading?: boolean
  hasMessages?: boolean
}

export function ChatInput({ input, setInput, onSubmit, isLoading = false, hasMessages = false }: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, window.innerHeight * 0.75) + 'px'
    }
  }, [input])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSubmit(input.trim())
      setInput("")
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleSuggestedAction = (suggestion: string) => {
    setInput(suggestion)
  }

  return (
    <div className={`mx-auto px-4 bg-background w-full lg:max-w-[800px] ${
      hasMessages ? 'pb-2 md:pb-3' : 'pb-4 md:pb-6'
    }`}>
      <form 
        className="flex gap-2 w-full"
        onSubmit={handleSubmit}
      >
        <div className="relative w-full flex flex-col gap-4">
          {/* Suggested Actions - only show when input is empty and no messages */}
          {!input.trim() && !hasMessages && (
            <SuggestedActions onSuggestionClick={handleSuggestedAction} />
          )}

        {/* Hidden file input */}
        <input 
          className="fixed -top-4 -left-4 size-0.5 opacity-0 pointer-events-none" 
          multiple 
          tabIndex={-1} 
          type="file" 
        />

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          className="flex w-full border border-input px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm min-h-[24px] max-h-[calc(75dvh)] overflow-hidden resize-none rounded-2xl !text-base bg-muted pb-10 dark:border-zinc-700"
          data-testid="multimodal-input"
          placeholder="Send a message..."
          rows={2}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />

        {/* Attachment Button - Bottom Left */}
        <div className="absolute bottom-0 p-2 w-fit flex flex-row justify-start">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:text-accent-foreground rounded-md rounded-bl-lg p-[7px] h-fit dark:border-zinc-700 hover:dark:bg-zinc-900 hover:bg-zinc-200"
            data-testid="attachments-button"
          >
            <Paperclip className="h-[14px] w-[14px] -rotate-45" />
          </Button>
        </div>

        {/* Send Button - Bottom Right */}
        <div className="absolute bottom-0 right-0 p-2 w-fit flex flex-row justify-end">
          <Button
            type="submit"
            className="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 rounded-full p-1.5 h-fit border dark:border-zinc-600"
            data-testid="send-button"
            disabled={!input.trim() || isLoading}
          >
            <ArrowUp className="h-[14px] w-[14px]" />
          </Button>
        </div>
      </div>
    </form>
    </div>
  )
}