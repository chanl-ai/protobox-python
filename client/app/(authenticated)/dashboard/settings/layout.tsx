"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { 
  User, 
  Bell, 
  Shield, 
  Palette, 
  Globe, 
  Database,
  Key,
  CreditCard,
  Users,
  ChevronRight
} from "lucide-react"

interface SettingsLayoutProps {
  children: React.ReactNode
}

const settingsNav = [
  {
    href: "/dashboard/settings/general",
    label: "General",
    icon: User,
    description: "Basic account settings",
  },
  {
    href: "/dashboard/settings/notifications",
    label: "Notifications",
    icon: Bell,
    description: "Email and push notifications",
  },
  {
    href: "/dashboard/settings/security",
    label: "Security",
    icon: Shield,
    description: "Password and authentication",
  },
  {
    href: "/dashboard/settings/appearance",
    label: "Appearance",
    icon: Palette,
    description: "Theme and display preferences",
  },
  {
    href: "/dashboard/settings/api",
    label: "API Keys",
    icon: Key,
    description: "Manage API access",
  },
  {
    href: "/dashboard/settings/billing",
    label: "Billing",
    icon: CreditCard,
    description: "Plans and payment methods",
  },
  {
    href: "/dashboard/settings/team",
    label: "Team",
    icon: Users,
    description: "Team members and roles",
  },
  {
    href: "/dashboard/settings/integrations",
    label: "Integrations",
    icon: Globe,
    description: "Third-party connections",
  },
  {
    href: "/dashboard/settings/advanced",
    label: "Advanced",
    icon: Database,
    description: "Data and privacy settings",
  },
]

export default function SettingsLayout({ children }: SettingsLayoutProps) {
  const pathname = usePathname()

  return (
    <div className="flex flex-col space-y-6">
      {/* Page Header */}
      <div className="border-b pb-4">
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account settings and preferences</p>
      </div>

      {/* Two Column Layout */}
      <div className="flex gap-6">
        {/* Left Sidebar Navigation */}
        <aside className="w-64 space-y-1">
          <nav className="space-y-1">
            {settingsNav.map((item) => {
              const Icon = item.icon
              const isActive = pathname === item.href
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-secondary text-secondary-foreground"
                      : "hover:bg-secondary/50"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="h-4 w-4" />
                    <div className="text-left">
                      <div className="font-medium">{item.label}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.description}
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 opacity-50" />
                </Link>
              )
            })}
          </nav>
        </aside>

        {/* Right Content Area */}
        <div className="flex-1">
          {children}
        </div>
      </div>
    </div>
  )
}