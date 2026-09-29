import { AuthError } from '../types'

// Firebase Auth Error Codes
export const AUTH_ERROR_CODES = {
  // Sign In Errors
  'auth/invalid-credential': 'Invalid email or password.',
  'auth/wrong-password': 'Invalid email or password.',
  'auth/user-not-found': 'No user found with this email.',
  'auth/user-disabled': 'This account has been disabled.',
  
  // Sign Up Errors
  'auth/email-already-in-use': 'This email is already registered.',
  'auth/weak-password': 'Password must be at least 6 characters.',
  'auth/invalid-email': 'Please enter a valid email address.',
  
  // General Errors
  'auth/network-request-failed': 'Network error. Please check your connection.',
  'auth/too-many-requests': 'Too many failed attempts. Please try again later.',
  'auth/popup-closed-by-user': 'Sign in was cancelled.',
  'auth/operation-not-allowed': 'This sign in method is not enabled.',
  
  // OAuth Errors
  'auth/account-exists-with-different-credential': 'An account already exists with the same email.',
  'auth/auth-domain-config-required': 'Authentication configuration error.',
  'auth/cancelled-popup-request': 'Another sign in popup is already open.',
  
  // Token Errors
  'auth/invalid-custom-token': 'Invalid authentication token.',
  'auth/custom-token-mismatch': 'Token mismatch error.',
  
  // Other
  'auth/internal-error': 'An internal error occurred. Please try again.',
} as const

export function getAuthErrorMessage(error: any): string {
  // Check if it's a Firebase Auth error
  if (error?.code && AUTH_ERROR_CODES[error.code as keyof typeof AUTH_ERROR_CODES]) {
    return AUTH_ERROR_CODES[error.code as keyof typeof AUTH_ERROR_CODES]
  }
  
  // Check for network errors
  if (error?.message?.includes('Failed to fetch')) {
    return 'Connection error. Please check your internet connection.'
  }
  
  // Default error message
  return error?.message || 'An unexpected error occurred. Please try again.'
}

export function createAuthError(code: string, message?: string): AuthError {
  return {
    code,
    message: message || getAuthErrorMessage({ code }),
    originalError: null
  }
}

export function isAuthError(error: any): error is AuthError {
  return error && 
    typeof error === 'object' && 
    'code' in error && 
    'message' in error
}