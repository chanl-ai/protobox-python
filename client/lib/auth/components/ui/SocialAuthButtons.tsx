"use client"

import React from 'react'
import { AppleIcon, GoogleIcon, FacebookIcon } from '../icons'

interface SocialAuthButtonsProps {
  onGoogleClick?: () => void
  onAppleClick?: () => void
  onFacebookClick?: () => void
  loading?: boolean
  showGoogle?: boolean
  showApple?: boolean
  showFacebook?: boolean
  components?: {
    Button?: React.ComponentType<any>
  }
}

export function SocialAuthButtons({
  onGoogleClick,
  onAppleClick,
  onFacebookClick,
  loading = false,
  showGoogle = true,
  showApple = true,
  showFacebook = true,
  components = {}
}: SocialAuthButtonsProps) {
  const Button = components.Button || 'button'
  
  const visibleProviders = [
    showApple && { name: 'Apple', icon: AppleIcon, onClick: onAppleClick },
    showGoogle && { name: 'Google', icon: GoogleIcon, onClick: onGoogleClick },
    showFacebook && { name: 'Facebook', icon: FacebookIcon, onClick: onFacebookClick }
  ].filter(Boolean) as Array<{ name: string; icon: React.FC; onClick?: () => void }>

  if (visibleProviders.length === 0) return null

  return (
    <>
      <div className="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t after:border-border">
        <span className="relative z-10 bg-background px-2 text-muted-foreground">
          Or continue with
        </span>
      </div>
      
      <div className={`grid gap-4 grid-cols-${visibleProviders.length}`}>
        {visibleProviders.map(({ name, icon: Icon, onClick }) => {
          const buttonProps: any = {
            key: name,
            type: 'button',
            className: 'w-full',
            onClick: onClick,
            disabled: loading || !onClick
          }
          
          // Only add variant if Button supports it
          if (Button !== 'button') {
            buttonProps.variant = 'outline'
          }
          
          return (
            <Button {...buttonProps}>
              <Icon />
              <span className="sr-only">Continue with {name}</span>
            </Button>
          )
        })}
      </div>
    </>
  )
}