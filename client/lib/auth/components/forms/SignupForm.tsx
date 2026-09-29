"use client"

import React, { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { toast } from 'sonner'
import { AppleIcon, GoogleIcon, FacebookIcon } from '../icons'
import { getButtonProps } from '../utils'

interface SignupFormProps {
  className?: string
  onSuccess?: (user: any) => void
  onError?: (error: any) => void
  showSocialAuth?: boolean
  showNameFields?: boolean
  brandName?: string
  customValidation?: (data: { 
    email: string
    password: string
    firstName?: string
    lastName?: string 
  }) => { isValid: boolean; error?: string }
  components?: {
    Button?: React.ComponentType<any>
    Input?: React.ComponentType<any>
    Label?: React.ComponentType<any>
    Link?: React.ComponentType<any>
  }
}

export function SignupForm({
  className = '',
  onSuccess,
  onError,
  showSocialAuth = true,
  showNameFields = true,
  brandName = 'our app',
  customValidation,
  components = {}
}: SignupFormProps) {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  
  const { signUp, signInWithGoogle, signInWithApple, signInWithFacebook } = useAuth()

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
      const validation = customValidation({ email, password, firstName, lastName })
      if (!validation.isValid) {
        toast.error(validation.error || 'Validation failed')
        setLoading(false)
        return
      }
    }

    try {
      const displayName = showNameFields && (firstName || lastName) 
        ? `${firstName} ${lastName}`.trim() 
        : undefined
        
      await signUp(email, password, displayName)
      toast.success('Account created! Please check your email to verify.')
      setSuccess(true)
      onSuccess?.(null) // TODO: pass user object
    } catch (err: any) {
      let errorMessage = ''
      
      // Handle specific Firebase error messages
      if (err.code === 'auth/email-already-in-use') {
        errorMessage = 'This email is already registered. Please login instead.'
      } else if (err.code === 'auth/weak-password') {
        errorMessage = 'Password must be at least 6 characters long.'
      } else if (err.code === 'auth/invalid-email') {
        errorMessage = 'Please enter a valid email address.'
      } else if (err.message?.includes('Failed to fetch')) {
        errorMessage = 'Connection error. Please check your internet connection.'
      } else {
        errorMessage = err.message || 'An error occurred during signup'
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
      switch (provider) {
        case 'google':
          await signInWithGoogle()
          break
        case 'apple':
          await signInWithApple()
          break
        case 'facebook':
          await signInWithFacebook()
          break
      }
      toast.success('Account created successfully!')
      onSuccess?.(null) // TODO: pass user object
    } catch (err: any) {
      const errorMessage = err.message || `Failed to sign up with ${provider}`
      setError(errorMessage)
      toast.error(errorMessage)
      onError?.(err)
    } finally {
      setLoadingProvider(null)
    }
  }

  const getButtonLoadingText = (isMainButton: boolean = false) => {
    if (isMainButton && loading) {
      return 'Creating account...'
    }
    return 'Create an account'
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
        <span className="sr-only">Sign up with {provider}</span>
      </>
    )
  }

  if (success) {
    return (
      <div className={className}>
        <div className="flex flex-col gap-6">
          <div className="flex flex-col items-center text-center">
            <h1 className="text-2xl font-bold">Check your email</h1>
            <p className="text-muted-foreground text-balance">
              We've sent a confirmation link to {email}
            </p>
          </div>
          <div className="text-center text-sm text-muted-foreground">
            <p>
              Please check your email and click the confirmation link to complete your registration.
            </p>
          </div>
          <Button 
            onClick={() => window.location.href = '/login'} 
            className="w-full"
          >
            Go to Login
          </Button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className={className}>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col items-center text-center">
          <h1 className="text-2xl font-bold">Create an account</h1>
          <p className="text-muted-foreground text-balance">
            Sign up to get started with {brandName}
          </p>
        </div>
        
        <div className="grid gap-3">
          {showNameFields && (
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-2">
                <Label htmlFor="first-name">First name</Label>
                <Input 
                  id="first-name" 
                  placeholder="Max" 
                  value={firstName}
                  onChange={(e: any) => setFirstName(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="last-name">Last name</Label>
                <Input 
                  id="last-name" 
                  placeholder="Robinson" 
                  value={lastName}
                  onChange={(e: any) => setLastName(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>
          )}
          
          <div className="grid gap-2">
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
          
          <div className="grid gap-2">
            <Label htmlFor="password">Password</Label>
            <Input 
              id="password" 
              type="password" 
              required 
              value={password}
              onChange={(e: any) => setPassword(e.target.value)}
              disabled={loading}
            />
          </div>
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
          Already have an account?{" "}
          <Link href="/login" className="underline underline-offset-4">
            Sign in
          </Link>
        </div>
      </div>
    </form>
  )
}

