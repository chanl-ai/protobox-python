import { PartnerSidebar } from "@/components/partner-sidebar"
import { PartnerSiteHeader } from "@/components/partner-site-header"
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar"

interface PartnerLayoutProps {
  children: React.ReactNode
  params: Promise<{ partnerId: string }>
}

export default async function PartnerLayout({ children, params }: PartnerLayoutProps) {
  const { partnerId } = await params
  
  return (
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 64)",
          "--sidebar-width-icon": "calc(var(--spacing) * 12)", 
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <PartnerSidebar partnerId={partnerId} variant="inset" />
      <SidebarInset>
        <PartnerSiteHeader />
        <div className="flex flex-1 flex-col gap-4 p-8">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}