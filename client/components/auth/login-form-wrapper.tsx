"use client"

import { LoginForm } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import Link from "next/link"
import { AuthFormWrapper } from "./auth-form-wrapper"
import { logger } from "@/lib/logger"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { useEffect } from "react"

export function LoginFormWrapper() {
  const router = useRouter()
  const { workspaces, isAuthenticated } = useAuth()
  
  // Add a useEffect to check auth state after mount
  useEffect(() => {
    if (isAuthenticated && workspaces.length > 0) {
      logger.log('[LoginFormWrapper] Already authenticated, redirecting...')
      router.push('/dashboard')
    }
  }, [isAuthenticated, workspaces, router])
  
  const handleLoginSuccess = (user: any) => {
    logger.log('[LoginFormWrapper] Login successful for user:', user?.email)
    // Force redirect after a small delay to ensure auth state is updated
    setTimeout(() => {
      logger.log('[LoginFormWrapper] Forcing redirect to dashboard')
      router.push('/dashboard')
    }, 1000)
  }

  return (
    <AuthFormWrapper>
      <LoginForm
        brandName="ProtoBox"
        components={{
          Button,
          Input,
          Label,
          Link: Link as any
        }}
        showSocialAuth={true}
        showPasswordReset={true}
        onSuccess={handleLoginSuccess}
      />
    </AuthFormWrapper>
  )
}