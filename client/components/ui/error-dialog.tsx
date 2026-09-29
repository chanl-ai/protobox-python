"use client"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { AlertTriangle } from "lucide-react"

interface ErrorDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title?: string
  message: string
  details?: string
  onRetry?: () => void
  retryText?: string
}

export function ErrorDialog({
  open,
  onOpenChange,
  title = "Error",
  message,
  details,
  onRetry,
  retryText = "Retry"
}: ErrorDialogProps) {
  const handleClose = () => {
    onOpenChange(false)
  }

  const handleRetry = () => {
    if (onRetry) {
      onRetry()
    }
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            {title}
          </DialogTitle>
          <DialogDescription>
            {message}
          </DialogDescription>
          {details && (
            <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800 font-mono">{details}</p>
            </div>
          )}
        </DialogHeader>
        
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={handleClose}
          >
            Close
          </Button>
          {onRetry && (
            <Button
              type="button"
              onClick={handleRetry}
            >
              {retryText}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}