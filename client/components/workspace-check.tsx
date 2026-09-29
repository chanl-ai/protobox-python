"use client"

import { RequireAuth } from '@/lib/auth'

interface WorkspaceCheckProps {
  children: React.ReactNode
}

export function WorkspaceCheck({ children }: WorkspaceCheckProps) {
  
  return (
    <RequireAuth 
      redirectTo="/login"
      loadingComponent={
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-e-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
            <h2 className="mt-4 text-lg font-semibold">Loading workspace...</h2>
          </div>
        </div>
      }
    >
      {children}
    </RequireAuth>
  )
}