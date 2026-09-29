"use client"

import { useSearchParams } from "next/navigation"
import { useEffect } from "react"
import { Loader2 } from "lucide-react"

export default function DemoOAuthContent() {
  const searchParams = useSearchParams()
  const integration = searchParams.get("integration") || "unknown"
  
  useEffect(() => {
    // Auto-close after animation
    const timer = setTimeout(() => {
      if (window.opener) {
        window.opener.postMessage({
          type: "oauth-complete",
          integration
        }, "*")
      }
      window.close()
    }, 2000)
    
    return () => clearTimeout(timer)
  }, [integration])
  
  // Get nice names
  const integrationNames: Record<string, string> = {
    google_calendar: "Google Calendar",
    hubspot: "HubSpot",
    slack: "Slack",
    salesforce: "Salesforce",
    stripe: "Stripe",
    shopify: "Shopify"
  }
  
  const name = integrationNames[integration] || integration
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full mx-4">
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Authorization Successful!
          </h2>
          
          <p className="text-gray-600 mb-6">
            You've successfully connected {name} to your account.
          </p>
          
          <div className="flex items-center justify-center text-sm text-gray-500">
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            Closing window...
          </div>
        </div>
        
        <div className="mt-8 pt-4 border-t border-gray-200">
          <p className="text-xs text-center text-gray-400">
            This is a demo OAuth flow. In production, you would be redirected to {name}'s actual authorization page.
          </p>
        </div>
      </div>
    </div>
  )
}