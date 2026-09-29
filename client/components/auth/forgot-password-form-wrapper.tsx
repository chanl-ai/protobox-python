"use client"

import { ForgotPasswordForm } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import Link from "next/link"
import { AuthFormWrapper } from "./auth-form-wrapper"

export function ForgotPasswordFormWrapper() {
  return (
    <AuthFormWrapper>
      <ForgotPasswordForm
        brandName="ProtoBox"
        components={{
          Button,
          Input,
          Label,
          Link: Link as any
        }}
      />
    </AuthFormWrapper>
  )
}