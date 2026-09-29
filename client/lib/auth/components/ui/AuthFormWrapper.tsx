import React from 'react'

interface AuthFormWrapperProps {
  children: React.ReactNode
  className?: string
  showImage?: boolean
  brandName?: string
  brandLogo?: React.ReactNode
  brandTagline?: string
  brandDescription?: string
  termsUrl?: string
  privacyUrl?: string
  components?: {
    Card?: React.ComponentType<any>
    CardContent?: React.ComponentType<any>
  }
}

export function AuthFormWrapper({ 
  children, 
  className = '',
  showImage = true,
  brandName = 'YourApp',
  brandLogo,
  brandTagline = 'Welcome to our platform',
  brandDescription = 'Start building amazing things today.',
  termsUrl = '/terms',
  privacyUrl = '/privacy',
  components = {}
}: AuthFormWrapperProps) {
  // Default components (can be overridden)
  const Card = components.Card || 'div'
  const CardContent = components.CardContent || 'div'

  return (
    <div className={`flex flex-col gap-6 ${className}`}>
      <Card className="overflow-hidden p-0">
        <CardContent className="grid p-0 md:grid-cols-2">
          <div className="p-6 md:p-8">
            {children}
          </div>
          {showImage && (
            <div className="relative hidden md:block bg-gradient-to-br from-gray-900 to-gray-800 dark:from-gray-950 dark:to-gray-900">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-primary/10 to-transparent" />
              <div className="relative flex h-full flex-col justify-between p-8 text-white">
                <div className="flex items-center gap-2">
                  {brandLogo || (
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10 backdrop-blur-sm">
                      <svg
                        className="h-5 w-5 text-white"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2}
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M13 10V3L4 14h7v7l9-11h-7z"
                        />
                      </svg>
                    </div>
                  )}
                  <span className="text-lg font-semibold">{brandName}</span>
                </div>
                <div className="space-y-2">
                  <h2 className="text-2xl font-bold">
                    {brandTagline}
                  </h2>
                  <p className="text-sm text-gray-200 opacity-90">
                    {brandDescription}
                  </p>
                </div>
                <p className="text-xs text-gray-300 opacity-70">
                  Trusted by developers and businesses worldwide
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      <div className="text-muted-foreground text-center text-xs text-balance">
        By clicking continue, you agree to our{' '}
        <a href={termsUrl} className="underline underline-offset-4 hover:text-primary">
          Terms of Service
        </a>{' '}
        and{' '}
        <a href={privacyUrl} className="underline underline-offset-4 hover:text-primary">
          Privacy Policy
        </a>.
      </div>
    </div>
  )
}