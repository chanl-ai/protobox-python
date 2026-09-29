import { redirect } from 'next/navigation'

export default function AnalyticsPage() {
  // Redirect to main dashboard which contains analytics
  redirect('/dashboard')
}