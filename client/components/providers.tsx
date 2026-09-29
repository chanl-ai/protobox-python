'use client'

import { ThemeProvider } from "next-themes"
import { AuthProvider } from "@/lib/auth/providers/AuthProvider"
import { ProtoboxQueryProvider } from "@/lib/api/query-client"
import { FirebaseInit } from "./firebase-init"

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY!,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN!,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID!,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET!,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID!,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID!
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <ProtoboxQueryProvider>
        <AuthProvider firebaseConfig={firebaseConfig}>
          <FirebaseInit />
          {children}
        </AuthProvider>
      </ProtoboxQueryProvider>
    </ThemeProvider>
  )
}