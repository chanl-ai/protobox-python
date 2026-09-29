"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/lib/auth/stores/auth.store"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import {
  IconDashboard,
  IconListDetails,
  IconKey,
  IconBrain,
  IconActivity,
  IconChartBar,
  IconClipboardList,
  IconSettings,
  IconPlug,
  IconRobot,
  IconMessages,
  IconFileAi,
} from "@tabler/icons-react"

interface SearchCommandProps {
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function SearchCommand({ open, onOpenChange }: SearchCommandProps) {
  const router = useRouter()
  const { currentWorkspace } = useAuthStore()

  const runCommand = React.useCallback((command: () => void) => {
    onOpenChange?.(false)
    command()
  }, [onOpenChange])

  const navigationItems = [
    {
      group: "Main",
      items: [
        {
          title: "Dashboard",
          icon: IconDashboard,
          onSelect: () => runCommand(() => router.push("/dashboard")),
        },
        {
          title: "Actions",
          icon: IconListDetails,
          onSelect: () => runCommand(() => router.push("/dashboard/actions")),
        },
        {
          title: "Workflows",
          icon: IconListDetails,
          onSelect: () => runCommand(() => router.push("/dashboard/workflows")),
        },
        {
          title: "Knowledge Base",
          icon: IconBrain,
          onSelect: () => runCommand(() => router.push("/dashboard/knowledge-base")),
        },
        {
          title: "Secrets",
          icon: IconKey,
          onSelect: () => runCommand(() => router.push("/dashboard/secrets")),
        },
        {
          title: "Executions",
          icon: IconActivity,
          onSelect: () => runCommand(() => router.push("/dashboard/executions")),
        },
        {
          title: "Analytics",
          icon: IconChartBar,
          onSelect: () => runCommand(() => router.push("/dashboard/analytics")),
        },
        {
          title: "Audit Logs",
          icon: IconClipboardList,
          onSelect: () => runCommand(() => router.push("/dashboard/audit-logs")),
        },
      ],
    },
    {
      group: "AI Playground",
      items: [
        {
          title: "Chat Assistant",
          icon: IconMessages,
          onSelect: () => runCommand(() => router.push("/dashboard/playground/chat")),
        },
        {
          title: "Conversations",
          icon: IconFileAi,
          onSelect: () => runCommand(() => router.push("/dashboard/playground/conversations")),
        },
      ],
    },
    {
      group: "Configuration",
      items: [
        {
          title: "Integrations",
          icon: IconPlug,
          onSelect: () => runCommand(() => router.push("/dashboard/integrations")),
        },
        {
          title: "Settings",
          icon: IconSettings,
          onSelect: () => runCommand(() => router.push("/dashboard/settings")),
        },
      ],
    },
  ]

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        {navigationItems.map((section) => (
          <React.Fragment key={section.group}>
            <CommandGroup heading={section.group}>
              {section.items.map((item) => (
                <CommandItem
                  key={item.title}
                  onSelect={item.onSelect}
                  className="flex items-center gap-2"
                >
                  <item.icon className="h-4 w-4" />
                  <span>{item.title}</span>
                </CommandItem>
              ))}
            </CommandGroup>
            {section !== navigationItems[navigationItems.length - 1] && (
              <CommandSeparator />
            )}
          </React.Fragment>
        ))}
      </CommandList>
    </CommandDialog>
  )
}