"use client"

import { cn } from "@/lib/utils"
import { Globe, Code } from "lucide-react"

interface ActionType {
  value: "REST" | "CODE_RUN"
  label: string
  description: string
  icon: React.ReactNode
}

const actionTypes: ActionType[] = [
  {
    value: "REST",
    label: "REST API",
    description: "Make HTTP requests to external APIs",
    icon: <Globe className="h-5 w-5" />
  },
  {
    value: "CODE_RUN",
    label: "Code Execution",
    description: "Run custom code in a secure environment",
    icon: <Code className="h-5 w-5" />
  },
]

interface ActionTypeSelectorProps {
  value?: string
  onChange: (value: string) => void
  columns?: 1 | 2 | 3 | 4
  required?: boolean
  error?: string
}

export function ActionTypeSelector({
  value,
  onChange,
  columns = 2,
  required = false,
  error
}: ActionTypeSelectorProps) {
  return (
    <div className="space-y-2">
      <div className={cn(
        "grid gap-3",
        columns === 1 && "grid-cols-1",
        columns === 2 && "grid-cols-1 sm:grid-cols-2",
        columns === 3 && "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
        columns === 4 && "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"
      )}>
        {actionTypes.map((type) => {
          const isSelected = value === type.value

          return (
            <button
              key={type.value}
              type="button"
              onClick={() => onChange(type.value)}
              className={cn(
                "relative flex items-start gap-3 rounded-lg border p-4",
                "transition-all hover:shadow-md",
                "focus:outline-none focus:ring-2 focus:ring-primary",
                isSelected
                  ? "border-primary bg-primary/5 ring-2 ring-primary ring-offset-2"
                  : "border-muted-foreground/25 hover:border-muted-foreground/50",
                error && "border-destructive"
              )}
            >
              <div className={cn(
                "flex h-10 w-10 items-center justify-center rounded-md",
                isSelected ? "bg-primary/10" : "bg-muted",
                isSelected ? "text-primary" : "text-muted-foreground"
              )}>
                {type.icon}
              </div>
              <div className="flex-1 text-left">
                <p className="text-sm font-medium">{type.label}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {type.description}
                </p>
              </div>
              {isSelected && (
                <div className="absolute top-2 right-2">
                  <div className="h-2 w-2 rounded-full bg-primary" />
                </div>
              )}
            </button>
          )
        })}
      </div>
      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
    </div>
  )
}

// Export the action types for use in other components
export { actionTypes }
export type { ActionType }