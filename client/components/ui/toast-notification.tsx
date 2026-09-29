"use client"

import { useState, useEffect } from "react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { CheckCircle, XCircle, Info, AlertTriangle, X } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ToastNotificationProps {
  message: string
  type?: "success" | "error" | "info" | "warning"
  duration?: number
  onClose?: () => void
}

const typeConfig = {
  success: {
    icon: CheckCircle,
    className: "border-green-200 bg-green-50 text-green-800",
    iconColor: "text-green-500"
  },
  error: {
    icon: XCircle,
    className: "border-red-200 bg-red-50 text-red-800", 
    iconColor: "text-red-500"
  },
  info: {
    icon: Info,
    className: "border-blue-200 bg-blue-50 text-blue-800",
    iconColor: "text-blue-500"
  },
  warning: {
    icon: AlertTriangle,
    className: "border-orange-200 bg-orange-50 text-orange-800",
    iconColor: "text-orange-500"
  }
}

export function ToastNotification({
  message,
  type = "info",
  duration = 5000,
  onClose
}: ToastNotificationProps) {
  const [isVisible, setIsVisible] = useState(true)
  const config = typeConfig[type]
  const Icon = config.icon

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        handleClose()
      }, duration)

      return () => clearTimeout(timer)
    }
  }, [duration])

  const handleClose = () => {
    setIsVisible(false)
    if (onClose) {
      setTimeout(onClose, 150) // Allow fade out animation
    }
  }

  if (!isVisible) return null

  return (
    <div className="fixed top-4 right-4 z-50 w-full max-w-sm">
      <Alert className={`${config.className} relative`}>
        <Icon className={`h-4 w-4 ${config.iconColor}`} />
        <AlertDescription className="pr-8">
          {message}
        </AlertDescription>
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 h-6 w-6 p-0 hover:bg-black/10"
          onClick={handleClose}
        >
          <X className="h-3 w-3" />
        </Button>
      </Alert>
    </div>
  )
}

// Hook for managing multiple toasts
export function useToast() {
  const [toasts, setToasts] = useState<Array<{
    id: string
    message: string
    type: "success" | "error" | "info" | "warning"
  }>>([])

  const addToast = (message: string, type: "success" | "error" | "info" | "warning" = "info") => {
    const id = Date.now().toString()
    setToasts(prev => [...prev, { id, message, type }])
  }

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }

  const ToastContainer = () => (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map(toast => (
        <ToastNotification
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  )

  return {
    toast: addToast,
    ToastContainer
  }
}