export interface FirebaseConfig {
  apiKey: string
  authDomain: string
  projectId: string
  storageBucket?: string
  messagingSenderId?: string
  appId: string
}

export interface UIConfig {
  theme?: 'light' | 'dark' | 'auto'
  logo?: string
  brandName?: string
  primaryColor?: string
  showSocialAuth?: boolean
  showPasswordReset?: boolean
  showEmailVerification?: boolean
}

export interface RouteConfig {
  login?: string
  signup?: string
  forgotPassword?: string
  resetPassword?: string
  dashboard?: string
  onboarding?: string
}

export interface RedirectConfig {
  // Redirects after successful authentication
  afterSignIn?: string
  afterSignUp?: string
  afterSignOut?: string
  
  // Redirect when user is not authenticated
  requireAuth?: string
  
  // Redirect when user has no workspace
  requireWorkspace?: string
  
  // Enable automatic workspace detection and redirect
  autoRedirectToWorkspace?: boolean
}

export interface BackendConfig {
  tokenExchangeUrl?: string
  customTokenEndpoint?: string
}

export interface DevConfig {
  enableTestMode?: boolean
  testUser?: {
    email: string
    name: string
  }
}

export interface FirebaseAuthConfig {
  firebase: FirebaseConfig
  ui?: UIConfig
  routes?: RouteConfig
  redirects?: RedirectConfig
  backend?: BackendConfig
  dev?: DevConfig
}