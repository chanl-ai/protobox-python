// Client-side auth exports

// Hooks
export { useAuth } from './hooks'

// Stores
// @deprecated For component usage, use useAuth() hook instead.
// useAuthStore should only be used internally by auth system or for performance-optimized selectors.
export { useAuthStore } from './stores/auth.store'

// Context and Provider
export { AuthProvider } from './context/AuthProvider'
export type { AuthUser } from './context/AuthContext'

// Components
export { LoginForm } from './components/forms/LoginForm'
export { SignupForm } from './components/forms/SignupForm'
export { ForgotPasswordForm } from './components/forms/ForgotPasswordForm'
export { RequireAuth } from './components/RequireAuth'

// Utilities
export * from './utils/storage'

// Backend integration
export { backendIntegration } from './backend-integration'