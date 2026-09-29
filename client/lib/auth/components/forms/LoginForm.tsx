"use client"

import React, { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { AuthUser } from '../../types'
import { toast } from 'sonner'
import { AppleIcon, GoogleIcon, FacebookIcon } from '../icons'
import { getButtonProps } from '../utils'

interface LoginFormProps {
  className?: string
  onSuccess?: (user: AuthUser) => void
  onError?: (error: any) => void
  redirectTo?: string
  showSocialAuth?: boolean
  showPasswordReset?: boolean
  customValidation?: (data: { email: string; password: string }) => { isValid: boolean; error?: string }
  brandName?: string
  // UI component props for customization
  components?: {
    Button?: React.ComponentType<any>
    Input?: React.ComponentType<any>
    Label?: React.ComponentType<any>
    Link?: React.ComponentType<any>
  }
}

export function LoginForm({
  className = '',
  onSuccess,
  onError,
  redirectTo,
  showSocialAuth = true,
  showPasswordReset = true,
  customValidation,
  brandName = 'our app',
  components = {}
}: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null)
  const [error, setError] = useState('')
  
  const { signIn, signInWithGoogle, signInWithApple, signInWithFacebook, user } = useAuth()

  // Default components (can be overridden)
  const Button = components.Button || 'button'
  const Input = components.Input || 'input'
  const Label = components.Label || 'label'
  const Link = components.Link || 'a'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    // Custom validation if provided
    if (customValidation) {
      const validation = customValidation({ email, password })
      if (!validation.isValid) {
        setError(validation.error || 'Validation failed')
        setLoading(false)
        return
      }
    }

    try {
      const user = await signIn(email, password)
      toast.success('Login successful!')
      if (user) onSuccess?.(user)
    } catch (err: any) {
      let errorMessage = ''
      
      // Handle specific Firebase error messages
      if (err.code === 'auth/invalid-credential' || err.code === 'auth/wrong-password' || err.code === 'auth/user-not-found') {
        errorMessage = 'Invalid email or password. Please try again.'
      } else if (err.code === 'auth/user-disabled') {
        errorMessage = 'This account has been disabled. Please contact support.'
      } else if (err.message?.includes('Failed to fetch')) {
        errorMessage = 'Connection error. Please check your internet connection.'
      } else {
        errorMessage = err.message || 'An error occurred during login'
      }
      
      setError(errorMessage)
      toast.error(errorMessage)
      onError?.(err)
    } finally {
      setLoading(false)
    }
  }

  const handleSocialLogin = async (provider: 'google' | 'apple' | 'facebook') => {
    setLoadingProvider(provider)
    setError('')
    
    try {
      let user
      switch (provider) {
        case 'google':
          user = await signInWithGoogle()
          break
        case 'apple':
          user = await signInWithApple()
          break
        case 'facebook':
          user = await signInWithFacebook()
          break
      }
      toast.success('Login successful!')
      if (user) {
        onSuccess?.(user)
      }
    } catch (err: any) {
      const errorMessage = err.message || `Failed to sign in with ${provider}`
      toast.error(errorMessage)
      onError?.(err)
    } finally {
      setLoadingProvider(null)
    }
  }

  const getButtonLoadingText = (isMainButton: boolean = false) => {
    if (isMainButton && loading) {
      return 'Signing in...'
    }
    return 'Login'
  }

  const getSocialButtonContent = (provider: 'google' | 'apple' | 'facebook') => {
    const icons = {
      google: <GoogleIcon />,
      apple: <AppleIcon />,
      facebook: <FacebookIcon />
    }
    
    if (loadingProvider === provider) {
      return (
        <>
          <span className="animate-pulse">Connecting...</span>
        </>
      )
    }
    
    return (
      <>
        {icons[provider]}
        <span className="sr-only">Login with {provider}</span>
      </>
    )
  }

  return (
    <form onSubmit={handleSubmit} className={className}>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col items-center text-center">
          <h1 className="text-2xl font-bold">Welcome back</h1>
          <p className="text-muted-foreground text-balance">
            Login to your {brandName} account
          </p>
        </div>
        
        <div className="grid gap-3">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="m@example.com"
            required
            value={email}
            onChange={(e: any) => setEmail(e.target.value)}
            disabled={loading}
          />
        </div>
        
        <div className="grid gap-3">
          <div className="flex items-center">
            <Label htmlFor="password">Password</Label>
            {showPasswordReset && (
              <Link
                href="/forgot-password"
                className="ml-auto text-sm underline-offset-2 hover:underline"
              >
                Forgot your password?
              </Link>
            )}
          </div>
          <Input 
            id="password" 
            type="password" 
            required 
            value={password}
            onChange={(e: any) => setPassword(e.target.value)}
            disabled={loading}
          />
        </div>
        
        {error && (
          <div className="text-red-600 dark:text-red-400 text-sm text-center p-3 bg-red-50 dark:bg-red-950/50 rounded-md border border-red-200 dark:border-red-800" role="alert">
            {error}
          </div>
        )}
        
        <Button type="submit" className="w-full" disabled={loading}>
          {getButtonLoadingText(true)}
        </Button>
        
        {showSocialAuth && (
          <>
            <div className="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t after:border-border">
              <span className="relative z-10 bg-background px-2 text-muted-foreground">
                Or continue with
              </span>
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              <Button 
                {...getButtonProps(Button, {
                  variant: 'outline',
                  type: 'button',
                  className: 'w-full',
                  onClick: () => handleSocialLogin('apple'),
                  disabled: loading || loadingProvider !== null
                })}
              >
                {getSocialButtonContent('apple')}
              </Button>
              
              <Button 
                {...getButtonProps(Button, {
                  variant: 'outline',
                  type: 'button',
                  className: 'w-full',
                  onClick: () => handleSocialLogin('google'),
                  disabled: loading || loadingProvider !== null
                })}
              >
                {getSocialButtonContent('google')}
              </Button>
              
              <Button 
                {...getButtonProps(Button, {
                  variant: 'outline',
                  type: 'button',
                  className: 'w-full',
                  onClick: () => handleSocialLogin('facebook'),
                  disabled: loading || loadingProvider !== null
                })}
              >
                {getSocialButtonContent('facebook')}
              </Button>
            </div>
          </>
        )}
        
        <div className="text-center text-sm">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="underline underline-offset-4">
            Sign up
          </Link>
        </div>
      </div>
    </form>
  )
}

