import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface LoadingStateProps {
  message?: string
  className?: string
  size?: "sm" | "md" | "lg"
}

export function LoadingState({ 
  message = "Loading...", 
  className,
  size = "md" 
}: LoadingStateProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-8 w-8", 
    lg: "h-12 w-12"
  }

  const containerClasses = {
    sm: "min-h-[100px]",
    md: "min-h-[400px]",
    lg: "min-h-[600px]"
  }

  return (
    <div className={cn("flex items-center justify-center", containerClasses[size], className)}>
      <div className="text-center">
        <Loader2 className={cn("animate-spin border-b-2 border-primary mx-auto mb-4", sizeClasses[size])} />
        <p className="text-muted-foreground">{message}</p>
      </div>
    </div>
  )
}