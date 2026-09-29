import { Suspense } from "react"
import DemoOAuthContent from "./demo-oauth-content"
import { Loader2 } from "lucide-react"

export default function DemoOAuthPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full mx-4">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-gray-600" />
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        </div>
      </div>
    }>
      <DemoOAuthContent />
    </Suspense>
  )
}