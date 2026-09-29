"use client"

import { Button } from "@/components/ui/button"

interface SuggestedActionsProps {
  onSuggestionClick: (suggestion: string) => void
}

const suggestions = [
  {
    title: "Help me set up",
    subtitle: "a new REST API action"
  },
  {
    title: "Show me my current",
    subtitle: "workspace configuration"
  },
  {
    title: "Help me configure",
    subtitle: "OAuth integrations"
  },
  {
    title: "How do I test",
    subtitle: "my MCP server locally?"
  }
]

export function SuggestedActions({ onSuggestionClick }: SuggestedActionsProps) {
  return (
    <div data-testid="suggested-actions" className="grid sm:grid-cols-2 gap-2 w-full">
      {suggestions.map((suggestion, index) => (
        <div 
          key={index}
          className={`block ${index >= 2 ? 'hidden sm:block' : ''}`}
          style={{ opacity: 1, transform: 'none' }}
        >
          <Button
            type="button"
            variant="outline"
            className="inline-flex whitespace-nowrap font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 hover:bg-accent hover:text-accent-foreground text-left border rounded-xl px-4 py-3.5 text-sm flex-1 gap-1 sm:flex-col w-full h-auto justify-start items-start"
            onClick={() => onSuggestionClick(`${suggestion.title} ${suggestion.subtitle}`)}
          >
            <span className="font-medium">{suggestion.title}</span>
            <span className="text-muted-foreground">{suggestion.subtitle}</span>
          </Button>
        </div>
      ))}
    </div>
  )
}