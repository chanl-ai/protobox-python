'use client'

import { useEffect } from 'react'

// Make debugging available globally in browser console
declare global {
  interface Window {
    debugFirebaseEnv: () => Record<string, string | undefined>
  }
}

if (typeof window !== 'undefined') {
  window.debugFirebaseEnv = () => {
    return {
      USE_EMULATOR: process.env.NEXT_PUBLIC_USE_FIREBASE_EMULATOR,
      EMULATOR_HOST: process.env.NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_HOST,
      API_URL: process.env.NEXT_PUBLIC_API_URL,
      PROJECT_ID: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
      NODE_ENV: process.env.NODE_ENV
    }
  }
}

export function FirebaseInit() {
  useEffect(() => {
    // Firebase initialization is now handled entirely in firebase.ts
    // This component just provides debugging utilities
    console.log('[FirebaseInit] Debug utilities available: window.debugFirebaseEnv()')
  }, [])
  
  return null
}