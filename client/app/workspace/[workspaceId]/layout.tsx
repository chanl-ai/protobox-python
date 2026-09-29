import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar"
import { WorkspaceCheck } from "@/components/workspace-check"

interface WorkspaceLayoutProps {
  children: React.ReactNode
  params: { workspaceId: string }
}

export default function WorkspaceLayout({ children, params }: WorkspaceLayoutProps) {
  return (
    <WorkspaceCheck>
        <SidebarProvider
        style={
          {
            "--sidebar-width": "calc(var(--spacing) * 64)",
            "--sidebar-width-icon": "calc(var(--spacing) * 12)",
            "--header-height": "calc(var(--spacing) * 12)",
          } as React.CSSProperties
        }
      >
        <AppSidebar variant="inset" />
        <SidebarInset>
          <SiteHeader />
          <div className="flex flex-1 flex-col">
            <div className="@container/main flex flex-1 flex-col gap-2">
              {/* Content starts here */}
              <div className="flex flex-col gap-6 p-8 md:gap-6 md:py-6">
                {children}
              </div>
              {/* Content ends here */}
            </div>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </WorkspaceCheck>
  )
}