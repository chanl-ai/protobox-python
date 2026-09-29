"use client"

import { usePathname, useParams } from "next/navigation"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { HelpCircle } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

interface BreadcrumbSegment {
  href?: string
  label: string
  isCurrentPage?: boolean
}

// Route segment to label mapping for partner routes
const SEGMENT_LABELS: Record<string, string> = {
  'partner': 'Partner',
  'dashboard': 'Dashboard',
  'analytics': 'Analytics',
  'workspaces': 'Workspaces',
  'team': 'Team',
  'settings': 'Settings',
  'billing': 'Billing',
  'api-keys': 'API Keys',
  'embeds': 'Embeds',
  'general': 'General',
  'test': 'Test'
}

export function PartnerSiteHeader() {
  const pathname = usePathname()
  const params = useParams()

  const generateBreadcrumbs = (): BreadcrumbSegment[] => {
    if (!pathname) return [{ label: 'Dashboard' }]

    const segments = pathname.split('/').filter(Boolean)
    const breadcrumbs: BreadcrumbSegment[] = []

    // Find the partner structure: partner/{partnerId}/...
    const partnerIndex = segments.findIndex(segment => segment === 'partner')
    if (partnerIndex === -1) return [{ label: 'Dashboard' }]

    // Get partner prefix for URL construction
    const partnerPrefix = segments.slice(0, partnerIndex + 2).join('/')
    const relevantSegments = segments.slice(partnerIndex + 2)

    // Add Partner root
    breadcrumbs.push({
      href: `/${partnerPrefix}/dashboard`,
      label: 'Partner'
    })

    relevantSegments.forEach((segment, index) => {
      const isLast = index === relevantSegments.length - 1
      let label = SEGMENT_LABELS[segment] || segment

      // Build href for non-last segments
      let href: string | undefined
      if (!isLast) {
        // Reconstruct the full path including partner prefix
        const pathSegments = [...partnerPrefix.split('/'), ...relevantSegments.slice(0, index + 1)]
        href = `/${pathSegments.join('/')}`
      }

      breadcrumbs.push({
        href,
        label,
        isCurrentPage: isLast
      })
    })

    return breadcrumbs
  }

  const breadcrumbs = generateBreadcrumbs()

  return (
    <header className="flex h-(--header-height) shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-(--header-height)">
      <div className="flex w-full items-center justify-between gap-1 px-4 lg:gap-2 lg:px-6">
        {/* Left side: Sidebar trigger and breadcrumbs */}
        <div className="flex items-center gap-1 lg:gap-2">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" />
          
          {/* Dynamic Breadcrumb Navigation */}
          <Breadcrumb>
            <BreadcrumbList>
              {breadcrumbs.map((crumb, index) => (
                <div key={index} className="flex items-center">
                  {index > 0 && <BreadcrumbSeparator />}
                  <BreadcrumbItem>
                    {crumb.isCurrentPage || !crumb.href ? (
                      <BreadcrumbPage className="font-medium">
                        {crumb.label}
                      </BreadcrumbPage>
                    ) : (
                      <BreadcrumbLink href={crumb.href} className="transition-colors hover:text-foreground">
                        {crumb.label}
                      </BreadcrumbLink>
                    )}
                  </BreadcrumbItem>
                </div>
              ))}
            </BreadcrumbList>
          </Breadcrumb>
        </div>

        {/* Right side: Help button */}
        <div className="flex items-center gap-2">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" size="sm" className="h-8">
                <HelpCircle className="h-4 w-4 mr-2" />
                Help
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Partner Dashboard Help</DialogTitle>
                <DialogDescription>
                  Get help with the ProtoBox Partner Dashboard
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium mb-1">Quick Links</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• <a href="https://github.com/chanl-ai/protobox-python/tree/main/docs" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">Partner Documentation</a></li>
                    <li>• <a href="https://github.com/chanl-ai/protobox-python/tree/main/docs" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">Embed Integration Guide</a></li>
                    <li>• <a href="https://github.com/chanl-ai/protobox-python/tree/main/docs" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">API Reference</a></li>
                  </ul>
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-1">Contact Support</h4>
                  <p className="text-sm text-muted-foreground">
                    Email us at <a href="https://github.com/chanl-ai/protobox-python/issues" className="underline hover:text-foreground">GitHub issues</a> for assistance.
                  </p>
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-1">Join Partner Community</h4>
                  <p className="text-sm text-muted-foreground">
                    Connect with other partners in our <a href="https://github.com/chanl-ai/protobox-python/discussions" target="_blank" rel="noopener noreferrer" className="underline hover:text-foreground">Partner Community Forum</a>.
                  </p>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>
    </header>
  )
}