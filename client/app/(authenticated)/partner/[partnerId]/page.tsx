import { redirect } from 'next/navigation'
import { use } from 'react'

interface PartnerRootProps {
  params: Promise<{ partnerId: string }>
}

export default function PartnerRoot({ params }: PartnerRootProps) {
  const { partnerId } = use(params)
  
  // Redirect to dashboard as the default partner page
  redirect(`/partner/${partnerId}/dashboard`)
}