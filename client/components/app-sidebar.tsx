"use client"

import * as React from "react"
import Link from "next/link"
import {
  IconCamera,
  IconDashboard,
  IconDatabase,
  IconFileAi,
  IconFileDescription,
  IconFileWord,
  IconHelp,
  IconListDetails,
  IconReport,
  IconSettings,
  IconKey,
  IconBrain,
  IconClipboardList,
  IconActivity,
  IconPlug,
  IconRobot,
  IconMessages,
  IconPlugConnected,
  IconSparkles,
  IconBulb,
  IconUsers,
  IconChartBar,
} from "@tabler/icons-react"
import { NavMain } from "@/components/nav-main"
import { NavSecondary } from "@/components/nav-secondary"
import { NavUser } from "@/components/nav-user"
import { WorkspaceSwitcher } from "@/components/workspace-switcher"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
} from "@/components/ui/sidebar"
import { useAuth } from "@/lib/auth"
import { useAuthStore } from "@/lib/auth/stores/auth.store"
import { useFeatureFlag } from "@/lib/features"

const useNavigationData = () => {
  const promptManagementEnabled = useFeatureFlag('promptManagement')
  const memoriesEnabled = useFeatureFlag('memories')

  const navData = React.useMemo(() => {
    // Playground section (always visible)
    const playground = {
      title: "Playground",
      url: "/dashboard/playground",
      icon: IconRobot,
      items: [
        {
          title: "Chat Assistant",
          url: "/dashboard/playground/chat",
          icon: IconMessages,
        },
        {
          title: "Conversations",
          url: "/dashboard/playground/conversations",
          icon: IconFileAi,
        },
      ],
    }

    // Define section - build dynamically based on features
    const navDefine = []

    if (promptManagementEnabled) {
      navDefine.push({
        title: "Prompts",
        url: "/dashboard/prompts",
        icon: IconFileAi,
      })
    }

    navDefine.push({
      title: "Knowledge Base",
      url: "/dashboard/knowledge-base",
      icon: IconBrain,
    })

    if (memoriesEnabled) {
      navDefine.push({
        title: "Memories",
        url: "/dashboard/memories",
        icon: IconBrain,
      })
    }

    navDefine.push(
      {
        title: "Actions",
        url: "/dashboard/actions",
        icon: IconListDetails,
      },
      {
        title: "Secrets",
        url: "/dashboard/secrets",
        icon: IconKey,
      }
    )

    // Connect section
    const navConnect = [
      {
        title: "Clients",
        url: "/dashboard/clients",
        icon: IconPlugConnected,
      },
      {
        title: "Integrations",
        url: "/dashboard/integrations",
        icon: IconPlug,
      },
      {
        title: "Team",
        url: "/dashboard/team",
        icon: IconUsers,
      },
    ]

    // Observe section
    const navObserve = [
      {
        title: "Activity",
        url: "/dashboard/executions",
        icon: IconActivity,
      },
      {
        title: "Analytics",
        url: "/dashboard/analytics",
        icon: IconChartBar,
      },
      {
        title: "Audit Logs",
        url: "/dashboard/audit-logs",
        icon: IconClipboardList,
      },
    ]

    return {
      playground,
      navDefine,
      navConnect,
      navObserve,
    }
  }, [promptManagementEnabled, memoriesEnabled])

  return navData
}

const data = {
  navSecondary: [
    {
      title: "Settings",
      url: "/dashboard/settings",
      icon: IconSettings,
      items: [
        {
          title: "General",
          url: "/dashboard/settings",
        },
        {
          title: "Billing",
          url: "/dashboard/settings/billing",
        },
        {
          title: "Security",
          url: "/dashboard/settings/security",
        },
      ],
    },
    {
      title: "Help & Docs",
      url: "#",
      icon: IconHelp,
    },
  ],
  navClouds: [
    {
      title: "Capture",
      icon: IconCamera,
      isActive: true,
      url: "#",
      items: [
        {
          title: "Active Proposals",
          url: "#",
        },
        {
          title: "Archived",
          url: "#",
        },
      ],
    },
    {
      title: "Proposal",
      icon: IconFileDescription,
      url: "#",
      items: [
        {
          title: "Active Proposals",
          url: "#",
        },
        {
          title: "Archived",
          url: "#",
        },
      ],
    },
    {
      title: "Prompts",
      icon: IconFileAi,
      url: "#",
      items: [
        {
          title: "Active Proposals",
          url: "#",
        },
        {
          title: "Archived",
          url: "#",
        },
      ],
    },
  ],
  navSecondary: [
    {
      title: "Audit Logs",
      url: "/dashboard/audit-logs",
      icon: IconClipboardList,
    },
    {
      title: "Settings",
      url: "/dashboard/settings",
      icon: IconSettings,
    },
    {
      title: "Get Help",
      url: "#",
      icon: IconHelp,
    },
  ],
  documents: [
    {
      name: "Data Library",
      url: "#",
      icon: IconDatabase,
    },
    {
      name: "Reports",
      url: "#",
      icon: IconReport,
    },
    {
      name: "Word Assistant",
      url: "#",
      icon: IconFileWord,
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { user } = useAuth()
  const { currentWorkspace } = useAuthStore()
  const { playground, navDefine, navConnect, navObserve } = useNavigationData()

  // Prepare user data for NavUser component
  const userData = {
    name: user?.displayName || user?.email?.split('@')[0] || 'User',
    email: user?.email || '',
    avatar: user?.photoURL || '',
  }

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <WorkspaceSwitcher />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {/* Playground at top */}
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild>
                  <Link href={playground.url}>
                    <playground.icon />
                    <span>{playground.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Define Section */}
        <SidebarGroup>
          <SidebarGroupLabel>Define</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navDefine.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <Link href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Connect Section */}
        <SidebarGroup>
          <SidebarGroupLabel>Connect</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navConnect.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <Link href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Observe Section */}
        <SidebarGroup>
          <SidebarGroupLabel>Observe</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navObserve.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <Link href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <NavSecondary items={data.navSecondary} className="mt-auto" />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={userData} />
      </SidebarFooter>
    </Sidebar>
  )
}
