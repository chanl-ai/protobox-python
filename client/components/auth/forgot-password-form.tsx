"use client"

import Link from "next/link"
import { useState } from "react"
import { ArrowLeft } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/lib/auth"
import { toast } from "sonner"
import { AuthFormWrapper } from "./auth-form-wrapper"

export function ForgotPasswordForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const { resetPassword } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      await resetPassword(email)
      toast.success('Password reset link sent to your email')
      setSuccess(true)
      setLoading(false)
    } catch (error: any) {
      toast.error(error.message || 'An error occurred while sending reset link')
      setLoading(false)
    }
  }

  if (success) {
    return (
      <AuthFormWrapper className={className} showImage={false}>
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
              <ArrowLeft className="size-3" />
              Back to login
            </Link>
          </div>
        </div>
      </AuthFormWrapper>
    )
  }

  return (
    <AuthFormWrapper className={className}>
      <form onSubmit={handleSubmit}>
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
                  onChange={(e) => setEmail(e.target.value)}
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
                  <ArrowLeft className="size-3" />
                  Back to login
                </Link>
              </div>
            </div>
          </form>
      </AuthFormWrapper>
  )
}