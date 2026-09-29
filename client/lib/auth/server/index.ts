// Server-side utilities that don't need "use client"
// Note: This file should only contain client-safe utilities
// Firebase Admin SDK has been moved to the backend

export { initializeFirebase, getFirebaseAuth } from '../utils/firebase'
export { 
  getToken, 
  storeToken, 
  removeToken,
  getRefreshToken,
  storeRefreshToken,
  removeRefreshToken,
  clearAllTokens
} from '../utils/storage'