"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

interface SelectableCardProps extends React.HTMLAttributes<HTMLDivElement> {
  selected?: boolean
  disabled?: boolean
  icon?: React.ReactNode
  title: string
  description?: string
  subdescription?: string
  badge?: string
  onSelect?: () => void
}

export function SelectableCard({
  selected = false,
  disabled = false,
  icon,
  title,
  description,
  subdescription,
  badge,
  onSelect,
  className,
  ...props
}: SelectableCardProps) {
  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      onClick={() => !disabled && onSelect?.()}
      onKeyDown={(e) => {
        if (!disabled && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault()
          onSelect?.()
        }
      }}
      className={cn(
        "relative flex cursor-pointer rounded-lg border p-4 transition-all",
        "hover:shadow-md focus:outline-none focus:ring-2 focus:ring-offset-2",
        selected
          ? "border-primary bg-primary/5"
          : "border-muted-foreground/25 hover:border-muted-foreground/50",
        disabled && "cursor-not-allowed opacity-50",
        className
      )}
      {...props}
    >
      {/* Selection indicator */}
      {selected && (
        <div className="absolute right-2 top-2">
          <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary">
            <Check className="h-3 w-3 text-primary-foreground" />
          </div>
        </div>
      )}

      {/* Badge */}
      {badge && (
        <div className="absolute right-2 top-2 rounded-md bg-secondary px-2 py-1 text-xs font-medium">
          {badge}
        </div>
      )}

      <div className="flex items-start gap-3">
        {/* Icon */}
        {icon && (
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted">
            {icon}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 space-y-1">
          <p className="text-sm font-medium leading-none">{title}</p>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
          {subdescription && (
            <p className="text-xs text-muted-foreground/70 mt-1 italic">
              e.g. {subdescription}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

interface SelectableCardGroupProps {
  children: React.ReactNode
  columns?: 1 | 2 | 3 | 4 | "auto"
  className?: string
}

export function SelectableCardGroup({
  children,
  columns = 2,
  className,
}: SelectableCardGroupProps) {
  const gridCols = {
    1: "grid-cols-1",
    2: "grid-cols-1 sm:grid-cols-2",
    3: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4",
    auto: "grid-cols-1 sm:grid-cols-2 md:grid-cols-3", // Responsive auto layout
  }

  return (
    <div className={cn("grid gap-3", gridCols[columns], className)}>
      {children}
    </div>
  )
}