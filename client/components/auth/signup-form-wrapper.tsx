"use client"

import { SignupForm } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import Link from "next/link"
import { AuthFormWrapper } from "./auth-form-wrapper"

export function SignupFormWrapper() {
  return (
    <AuthFormWrapper>
      <SignupForm
        brandName="ProtoBox"
        components={{
          Button,
          Input,
          Label,
          Link: Link as any
        }}
        showSocialAuth={true}
        showNameFields={true}
      />
    </AuthFormWrapper>
  )
}