"use client"

import React, { useEffect, useState } from 'react'
import { useLoadingStore } from '@/lib/stores/loading.store'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Loader2, 
  RefreshCw, 
  X, 
  Wifi, 
  WifiOff, 
  Server,
  Clock,
  AlertCircle,
  Rocket
} from 'lucide-react'

export function UniversalLoadingDialog() {
  const {
    isGlobalLoading,
    showDialog,
    currentMessage,
    error,
    coldStartDetected,
    activeRequests,
    retry,
    cancel,
    clearError,
  } = useLoadingStore()
  
  const [progress, setProgress] = useState(0)
  const [elapsedTime, setElapsedTime] = useState(0)
  
  // Calculate progress based on average response time
  useEffect(() => {
    if (!isGlobalLoading) {
      setProgress(0)
      setElapsedTime(0)
      return
    }
    
    const startTime = Date.now()
    const expectedDuration = coldStartDetected ? 20000 : 5000 // 20s for cold start, 5s normal
    
    const progressInterval = setInterval(() => {
      const elapsed = Date.now() - startTime
      setElapsedTime(Math.floor(elapsed / 1000))
      
      // Logarithmic progress (fast at start, slow at end)
      const rawProgress = (elapsed / expectedDuration) * 100
      const logProgress = Math.min(95, Math.log10(rawProgress + 1) * 45)
      setProgress(logProgress)
    }, 100)
    
    return () => clearInterval(progressInterval)
  }, [isGlobalLoading, coldStartDetected])
  
  // Determine which icon to show
  const getIcon = () => {
    if (error) {
      return <WifiOff className="h-8 w-8 text-destructive" />
    }
    if (coldStartDetected) {
      return <Rocket className="h-8 w-8 text-primary animate-pulse" />
    }
    if (elapsedTime > 10) {
      return <Clock className="h-8 w-8 text-warning animate-pulse" />
    }
    return <Server className="h-8 w-8 text-primary animate-pulse" />
  }
  
  // Format elapsed time
  const formatTime = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds}s`
    }
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }
  
  // Don't show dialog if not needed
  if (!showDialog && !error) {
    return null
  }
  
  return (
    <Dialog open={showDialog || !!error} onOpenChange={() => {}}>
      <DialogContent 
        className="sm:max-w-md"
        onPointerDownOutside={(e) => e.preventDefault()} // Prevent closing on click outside
        onEscapeKeyDown={(e) => e.preventDefault()} // Prevent closing on escape
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            {getIcon()}
            <span>
              {error ? 'Connection Error' : coldStartDetected ? 'Server Starting Up' : 'Processing Request'}
            </span>
          </DialogTitle>
          <DialogDescription className="pt-2">
            {error ? String(error.message || 'An error occurred') : currentMessage}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Progress bar for loading state */}
          {isGlobalLoading && !error && (
            <>
              <div className="space-y-2">
                <Progress value={progress} className="h-2" />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Elapsed: {formatTime(elapsedTime)}</span>
                  {coldStartDetected && (
                    <span className="text-primary">Cold start detected</span>
                  )}
                </div>
              </div>
              
              {/* Show active requests in development */}
              {process.env.NODE_ENV === 'development' && activeRequests.size > 0 && (
                <div className="rounded-lg bg-muted p-3 space-y-1">
                  <p className="text-xs font-medium text-muted-foreground">
                    Active Requests ({activeRequests.size}):
                  </p>
                  {Array.from(activeRequests.values()).slice(0, 3).map((req) => (
                    <p key={req.id} className="text-xs text-muted-foreground truncate">
                      • {req.endpoint || req.id}
                    </p>
                  ))}
                </div>
              )}
            </>
          )}
          
          {/* Cold start information */}
          {coldStartDetected && !error && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                The server is starting up after being idle. This typically takes 15-30 seconds.
                Thank you for your patience!
              </AlertDescription>
            </Alert>
          )}
          
          {/* Error state actions */}
          {error && (
            <div className="flex gap-2">
              {error.canRetry && (
                <Button onClick={retry} className="flex-1">
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Retry
                </Button>
              )}
              <Button 
                variant="outline" 
                onClick={() => {
                  clearError()
                  cancel()
                }}
                className="flex-1"
              >
                <X className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            </div>
          )}
          
          {/* Cancel option for long-running requests */}
          {!error && elapsedTime > 15 && (
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                onClick={cancel}
                className="w-full"
              >
                <X className="mr-2 h-4 w-4" />
                Cancel Request
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}