"use client"

import React, { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { toast } from 'sonner'
import { ArrowLeft } from 'lucide-react'

interface ForgotPasswordFormProps {
  className?: string
  onSuccess?: () => void
  onError?: (error: any) => void
  brandName?: string
  components?: {
    Button?: React.ComponentType<any>
    Input?: React.ComponentType<any>
    Label?: React.ComponentType<any>
    Link?: React.ComponentType<any>
  }
}

export function ForgotPasswordForm({
  className = '',
  onSuccess,
  onError,
  brandName = 'our app',
  components = {}
}: ForgotPasswordFormProps) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  
  const { resetPassword } = useAuth()

  // Default components (can be overridden)
  const Button = components.Button || 'button'
  const Input = components.Input || 'input'
  const Label = components.Label || 'label'
  const Link = components.Link || 'a'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await resetPassword(email)
      toast.success('Password reset link sent to your email')
      setSuccess(true)
      onSuccess?.()
    } catch (err: any) {
      const errorMessage = err.message || 'An error occurred while sending reset link'
      toast.error(errorMessage)
      onError?.(err)
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className={className}>
        <div className="flex flex-col gap-6">
          <div className="flex flex-col items-center text-center">
            <h1 className="text-2xl font-bold">Check your email</h1>
            <p className="text-muted-foreground text-balance">
              We've sent a password reset link to {email}
            </p>
          </div>
          <div className="text-center text-sm text-muted-foreground">
            <p>
              Please check your email and click the reset link to create a new password.
            </p>
          </div>
          <div className="text-center text-sm">
            <Link href="/login" className="inline-flex items-center gap-1 underline underline-offset-4">
              <ArrowLeft className="h-3 w-3" />
              Back to login
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className={className}>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col items-center text-center">
          <h1 className="text-2xl font-bold">Forgot your password?</h1>
          <p className="text-muted-foreground text-balance">
            Enter your email address and we'll send you a link to reset your password
          </p>
        </div>
        
        <div className="grid gap-3">
          <Label htmlFor="email">Email Address</Label>
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
        
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Sending...' : 'Send Reset Link'}
        </Button>
        
        <div className="text-center text-sm">
          Remember your password?{" "}
          <Link href="/login" className="underline underline-offset-4">
            Sign in
          </Link>
        </div>
        
        <div className="text-center text-sm">
          <Link href="/login" className="inline-flex items-center gap-1 underline underline-offset-4">
            <ArrowLeft className="h-3 w-3" />
            Back to login
          </Link>
        </div>
      </div>
    </form>
  )
}