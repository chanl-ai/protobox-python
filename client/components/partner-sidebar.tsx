"use client"

import * as React from "react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,  
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { 
  BarChart3,
  Users,
  Settings,
  Key,
  DollarSign,
  Home,
  Briefcase,
  Building2,
  FileText
} from "lucide-react"
import { NavUser } from "@/components/nav-user"
import { useAuth } from "@/lib/auth"

interface PartnerSidebarProps extends React.ComponentProps<typeof Sidebar> {
  partnerId: string
}

// Partner navigation items
const partnerNavItems = [
  {
    title: "Dashboard",
    url: "/dashboard",
    icon: Home,
    description: "Partner overview and stats"
  },
  {
    title: "Analytics",
    url: "/analytics", 
    icon: BarChart3,
    description: "Usage and performance metrics"
  },
  {
    title: "Workspaces", 
    url: "/workspaces",
    icon: Building2,
    description: "Manage customer workspaces"
  },
  {
    title: "Team",
    url: "/team",
    icon: Users,
    description: "Manage team members"
  },
  {
    title: "Settings",
    url: "/settings",
    icon: Settings,
    description: "Partner configuration"
  },
  {
    title: "Billing",
    url: "/billing",
    icon: DollarSign,
    description: "Revenue and payments"
  }
]

export function PartnerSidebar({ partnerId, ...props }: PartnerSidebarProps) {
  const { user } = useAuth()
  
  // Prepare user data for NavUser component
  const userData = {
    name: user?.displayName || "Partner User",
    email: user?.email || "",
    avatar: user?.photoURL || ""
  }
  
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <div>
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                  <Briefcase className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">Partner Dashboard</span>  
                  <span className="truncate text-xs">ID: {partnerId}</span>
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Partner Management</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {partnerNavItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.description}>
                    <a href={`/partner/${partnerId}${item.url}`}>
                      <item.icon />
                      <span>{item.title}</span>
                    </a>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild>
              <a href="https://github.com/chanl-ai/protobox-python/tree/main/docs" target="_blank" rel="noopener noreferrer">
                <FileText className="size-4" />
                <span>Documentation</span>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton asChild>
              <a href="/workspace">
                <Home className="size-4" />
                <span>Back to My Workspace</span>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <NavUser user={userData} />
      </SidebarFooter>
      
      <SidebarRail />
    </Sidebar>
  )
}