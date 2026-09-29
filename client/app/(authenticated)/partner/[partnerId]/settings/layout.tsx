"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { PageHeader } from "@/components/ui/page-header"
import { Separator } from "@/components/ui/separator"
import { use } from "react"

interface SettingsLayoutProps {
  children: React.ReactNode
  params: Promise<{ partnerId: string }>
}

const settingsNavItems = [
  {
    title: "General",
    href: "/settings",
    description: "Partner profile and basic settings"
  },
  {
    title: "API Keys", 
    href: "/settings/api-keys",
    description: "Manage authentication credentials"
  },
  {
    title: "Embeds",
    href: "/settings/embeds",
    description: "Integration embed configurations"
  }
]

export default function SettingsLayout({ children, params }: SettingsLayoutProps) {
  const pathname = usePathname()
  const { partnerId } = use(params)
  const basePath = `/partner/${partnerId}`

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        subtitle="Manage your partner account settings and configurations"
      />

      <div className="flex flex-col space-y-8 lg:flex-row lg:space-x-8 lg:space-y-0">
        <aside className="lg:w-48">
          <nav className="flex space-x-2 lg:flex-col lg:space-x-0 lg:space-y-1">
            {settingsNavItems.map((item) => (
              <Link
                key={item.href}
                href={`${basePath}${item.href}`}
                className={cn(
                  "inline-flex items-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 hover:text-accent-foreground h-9 px-4 py-2 hover:bg-muted justify-start",
                  pathname === `${basePath}${item.href}`
                    ? "bg-muted font-medium text-foreground"
                    : "text-muted-foreground"
                )}
              >
                {item.title}
              </Link>
            ))}
          </nav>
        </aside>
        <div className="flex-1">
          {children}
        </div>
      </div>
    </div>
  )
}