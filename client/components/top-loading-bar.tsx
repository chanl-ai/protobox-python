"use client"

import { useEffect, useState } from 'react'
import { useLoadingStore } from '@/lib/stores/loading.store'

export function TopLoadingBar() {
  const { isGlobalLoading, activeRequests } = useLoadingStore()
  const [progress, setProgress] = useState(0)
  const [visible, setVisible] = useState(false)
  
  useEffect(() => {
    if (isGlobalLoading) {
      // Show the bar
      setVisible(true)
      setProgress(10)
      
      // Animate progress
      const timer = setTimeout(() => setProgress(30), 100)
      const timer2 = setTimeout(() => setProgress(50), 300)
      const timer3 = setTimeout(() => setProgress(70), 600)
      const timer4 = setTimeout(() => setProgress(85), 1000)
      
      return () => {
        clearTimeout(timer)
        clearTimeout(timer2)
        clearTimeout(timer3)
        clearTimeout(timer4)
      }
    } else {
      // Complete and hide
      setProgress(100)
      const hideTimer = setTimeout(() => {
        setVisible(false)
        setProgress(0)
      }, 300)
      
      return () => clearTimeout(hideTimer)
    }
  }, [isGlobalLoading])
  
  if (!visible) return null
  
  return (
    <div className="fixed top-0 left-0 right-0 z-[100] pointer-events-none">
      <div 
        className="h-[2px] bg-primary transition-all duration-300 ease-out"
        style={{ 
          width: `${progress}%`,
          boxShadow: progress < 100 ? '0 0 10px rgba(59, 130, 246, 0.5)' : 'none'
        }}
      />
    </div>
  )
}