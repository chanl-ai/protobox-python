import { initializeApp, getApps, FirebaseApp } from 'firebase/app'
import { getAuth, Auth, connectAuthEmulator } from 'firebase/auth'
import { FirebaseConfig } from '../types'

let firebaseApp: FirebaseApp | null = null
let firebaseAuth: Auth | null = null

export function initializeFirebase(config: FirebaseConfig): { app: FirebaseApp; auth: Auth } {
  // Check if Firebase is already initialized
  if (firebaseApp && firebaseAuth) {
    return { app: firebaseApp, auth: firebaseAuth }
  }

  try {
    // Initialize Firebase only if it hasn't been initialized
    const existingApps = getApps()
    firebaseApp = existingApps.length === 0 
      ? initializeApp(config) 
      : existingApps[0]
    
    firebaseAuth = getAuth(firebaseApp)
    
    // Connect to Firebase emulator in development
    if (process.env.NODE_ENV === 'development' && 
        process.env.NEXT_PUBLIC_USE_FIREBASE_EMULATOR === 'true' &&
        typeof window !== 'undefined') {
      
      // Only connect to emulator if not already connected
      try {
        // Check if emulator is already connected by checking the config
        if (!firebaseAuth.config.emulator) {
          connectAuthEmulator(firebaseAuth, `http://${process.env.NEXT_PUBLIC_FIREBASE_AUTH_EMULATOR_HOST || 'localhost:9299'}`, { disableWarnings: true })
        }
      } catch (error) {
        // Emulator connection failed (may already be connected)
        if (process.env.NODE_ENV === 'development') {
          console.warn('[Firebase] Auth emulator connection failed (may already be connected):', error)
        }
      }
    }
    
    return { app: firebaseApp, auth: firebaseAuth }
  } catch (error) {
    console.error('[Firebase] Initialization failed:', error)
    throw error
  }
}

export function getFirebaseAuth(): Auth {
  if (!firebaseAuth) {
    throw new Error('Firebase auth not initialized. Call initializeFirebase first.')
  }
  return firebaseAuth
}