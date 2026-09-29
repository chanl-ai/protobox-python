"use client"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode[]
  className?: string
}

export function PageHeader({ 
  title, 
  subtitle, 
  actions = [], 
  className = "" 
}: PageHeaderProps) {
  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          {subtitle && (
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          )}
        </div>
        {actions.length > 0 && (
          <div className="flex items-center space-x-2">
            {actions.map((action, index) => (
              <div key={index}>{action}</div>
            ))}
          </div>
        )}
      </div>
      <Separator />
    </div>
  )
}