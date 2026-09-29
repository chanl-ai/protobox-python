"use client"

import { usePathname, useParams } from "next/navigation"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "@/components/ui/breadcrumb"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useEffect, useState } from "react"
import { useAuth } from "@/lib/auth"
import { protoboxClient } from "@/lib/api/protobox-client"
import type { PartnerStatus } from "@/lib/api/partners"
import { Copy, Check, Info, Key, Globe, Handshake, Rocket, Search, Settings } from "lucide-react"
import { PartnerConversionDialog } from "./partner-conversion-dialog"
import { useAuthStore } from "@/lib/auth/stores/auth.store"
import { SearchCommand } from "./search-command"
import { MCPTokenDialog } from "./mcp-token-dialog"

interface BreadcrumbSegment {
  href?: string
  label: string
  isCurrentPage?: boolean
}

// Route segment to label mapping
const SEGMENT_LABELS: Record<string, string> = {
  'dashboard': 'Dashboard',
  'actions': 'Actions',
  'secrets': 'Secrets',
  'settings': 'Settings',
  'users': 'Users',
  'analytics': 'Analytics',
  'audit-logs': 'Audit Logs',
  'edit': 'Edit',
  'create': 'Create',
  'new': 'New'
}

export function SiteHeader() {
  const pathname = usePathname()
  const params = useParams()
  const { user } = useAuth()
  const [entityNames, setEntityNames] = useState<Record<string, string>>({})
  const [copied, setCopied] = useState(false)
  const [partnerStatus, setPartnerStatus] = useState<PartnerStatus | null>(null)
  const [showPartnerDialog, setShowPartnerDialog] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [showMCPDialog, setShowMCPDialog] = useState(false)

  const { currentWorkspace } = useAuthStore()
  const workspaceId = currentWorkspace?.id
  

  // Add keyboard shortcut for search
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setSearchOpen(true)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  // Fetch entity names and partner status
  useEffect(() => {
    if (!user?.customToken || !workspaceId) return

    const fetchData = async () => {
      try {
        // No need to set auth token - cookies handle authentication
        const names: Record<string, string> = {}

        // Extract actionId from params if present
        const actionId = params?.actionId as string
        if (actionId) {
          try {
            const actionResponse = await protoboxClient.getAction(workspaceId || undefined, actionId)
            if (actionResponse.data) {
              names[actionId] = actionResponse.data.name
            }
          } catch (error) {
            // Silently handle error, will show ID instead of name
          }
        }

        // Extract secretId from params if present
        const secretId = params?.secretId as string
        if (secretId) {
          try {
            const secretResponse = await protoboxClient.getSecret(workspaceId || undefined, secretId)
            if (secretResponse.data) {
              names[secretId] = secretResponse.data.name
            }
          } catch (error) {
            // Silently handle error, will show ID instead of name
          }
        }

        setEntityNames(names)

        // Fetch partner status - TEMPORARILY DISABLED
        // try {
        //   const status = await partnerApi.checkPartnerStatus()
        //   setPartnerStatus(status)
        // } catch (error) {
        //   // User is not a partner or error occurred
        //   setPartnerStatus({ is_partner: false })
        // }
        setPartnerStatus({ is_partner: false })
      } catch (error) {
        // Silently handle error
      }
    }

    fetchData()
  }, [user?.customToken, workspaceId, params])

  const generateBreadcrumbs = (): BreadcrumbSegment[] => {
    if (!pathname) return [{ label: 'Dashboard' }]

    const segments = pathname.split('/').filter(Boolean)
    const breadcrumbs: BreadcrumbSegment[] = []

    // Find the dashboard segment
    const dashboardIndex = segments.findIndex(segment => segment === 'dashboard')
    if (dashboardIndex === -1) return [{ label: 'Dashboard' }]

    const relevantSegments = segments.slice(dashboardIndex)

    relevantSegments.forEach((segment, index) => {
      const isLast = index === relevantSegments.length - 1
      let label = SEGMENT_LABELS[segment] || segment

      // Handle dynamic segments (MongoDB ObjectIds)
      if (segment.length === 24 && /^[a-fA-F0-9]+$/.test(segment)) {
        const entityName = entityNames[segment]
        if (entityName) {
          label = entityName
        } else {
          // Show first 8 characters of ID as fallback
          label = `${segment.slice(0, 8)}...`
        }
      }

      // Build href for non-last segments
      let href: string | undefined
      if (!isLast) {
        // Reconstruct the path
        const pathSegments = relevantSegments.slice(0, index + 1)
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

  // MCP URL path constant
  const MCP_URL_PATH = `/mcp/${workspaceId}/sse`

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

        {/* Right side: Search, Partner button and MCP Server Connection */}
        <div className="flex items-center gap-2 lg:gap-4">
          {/* Search Button */}
          <Button
            variant="outline"
            size="sm"
            className="h-8 px-3 text-xs"
            onClick={() => setSearchOpen(true)}
          >
            <Search className="h-4 w-4 mr-2" />
            <span className="hidden lg:inline">Search</span>
            <kbd className="ml-2 pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 lg:inline-flex">
              <span className="text-xs">⌘</span>K
            </kbd>
          </Button>
          
          {/* MCP Server Connection - Visible endpoint with copy button */}
          {workspaceId && (
            <div className="hidden md:flex items-center gap-2">
              <div className="hidden xl:inline text-xs text-muted-foreground">MCP:</div>
              <div className="flex items-center gap-1">
                <Input
                  value={`${process.env.NEXT_PUBLIC_MCP_BASE_URL || 'http://localhost:8090'}${MCP_URL_PATH}`}
                  readOnly
                  className="h-8 w-32 lg:w-48 xl:w-64 text-xs font-mono bg-muted/50 border-muted-foreground/20 focus-visible:ring-0 focus-visible:ring-offset-0 cursor-pointer hover:bg-muted/70"
                  onClick={() => setShowMCPDialog(true)}
                  title="Click to manage MCP tokens"
                />
                
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={async () => {
                    const url = `${process.env.NEXT_PUBLIC_MCP_BASE_URL || 'http://localhost:8090'}${MCP_URL_PATH}`
                    try {
                      await navigator.clipboard.writeText(url)
                      setCopied(true)
                      setTimeout(() => setCopied(false), 2000)
                    } catch (error) {
                      console.error('Failed to copy:', error)
                    }
                  }}
                  className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                  title="Copy MCP server endpoint"
                >
                  {copied ? (
                    <Check className="h-3 w-3 text-green-600" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                </Button>
                
                {/* Info button to open MCP token dialog */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowMCPDialog(true)}
                  className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                  title="Manage MCP tokens"
                >
                  <Key className="h-3 w-3" />
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Partner Conversion Dialog */}
      <PartnerConversionDialog
        open={showPartnerDialog}
        onOpenChange={setShowPartnerDialog}
        onSuccess={(partnerId) => {
          // Update partner status after successful conversion
          setPartnerStatus({
            is_partner: true,
            partner_id: partnerId
          })
        }}
      />
      
      {/* Search Command Dialog */}
      <SearchCommand open={searchOpen} onOpenChange={setSearchOpen} />
      
      {/* MCP Token Dialog */}
      {workspaceId && (
        <MCPTokenDialog
          open={showMCPDialog}
          onOpenChange={setShowMCPDialog}
          workspaceId={workspaceId}
          mcpUrlPath={MCP_URL_PATH}
        />
      )}
    </header>
  )
}