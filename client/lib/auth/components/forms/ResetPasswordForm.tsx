"use client"

import React, { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { toast } from 'sonner'

interface ResetPasswordFormProps {
  className?: string
  onSuccess?: () => void
  onError?: (error: any) => void
  components?: {
    Button?: React.ComponentType<any>
    Input?: React.ComponentType<any>
    Label?: React.ComponentType<any>
    Link?: React.ComponentType<any>
  }
}

export function ResetPasswordForm({
  className = '',
  onSuccess,
  onError,
  components = {}
}: ResetPasswordFormProps) {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  
  const { updatePassword } = useAuth()

  // Default components (can be overridden)
  const Button = components.Button || 'button'
  const Input = components.Input || 'input'
  const Label = components.Label || 'label'
  const Link = components.Link || 'a'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (password !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }
    
    if (password.length < 6) {
      toast.error('Password must be at least 6 characters')
      return
    }
    
    setLoading(true)

    try {
      await updatePassword(password)
      toast.success('Password updated successfully!')
      onSuccess?.()
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to update password'
      toast.error(errorMessage)
      onError?.(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className={className}>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col items-center text-center">
          <h1 className="text-2xl font-bold">Reset your password</h1>
          <p className="text-muted-foreground text-balance">
            Enter your new password below
          </p>
        </div>
        
        <div className="grid gap-3">
          <div className="grid gap-2">
            <Label htmlFor="password">New Password</Label>
            <Input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e: any) => setPassword(e.target.value)}
              disabled={loading}
              placeholder="Enter new password"
            />
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="confirm-password">Confirm Password</Label>
            <Input
              id="confirm-password"
              type="password"
              required
              value={confirmPassword}
              onChange={(e: any) => setConfirmPassword(e.target.value)}
              disabled={loading}
              placeholder="Confirm new password"
            />
          </div>
        </div>
        
        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Updating...' : 'Reset Password'}
        </Button>
        
        <div className="text-center text-sm">
          <Link href="/login" className="underline underline-offset-4">
            Back to login
          </Link>
        </div>
      </div>
    </form>
  )
}