"use client"

import * as React from "react"
import { Check, ChevronsUpDown, Plus } from "lucide-react"

import { cn } from "@/lib/utils"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  SidebarMenuButton,
  useSidebar,
} from "@/components/ui/sidebar"
import { useAuthStore } from "@/lib/auth/stores/auth.store"

interface WorkspaceSwitcherProps {
  className?: string
}

export function WorkspaceSwitcher({
  className,
}: WorkspaceSwitcherProps) {
  const [open, setOpen] = React.useState(false)
  const [mounted, setMounted] = React.useState(false)
  const { isMobile, state } = useSidebar()
  
  // Always call hooks at the top level - never conditionally
  const { workspaces, currentWorkspace, workspaceLoading, selectWorkspace, refreshWorkspaces } = useAuthStore()
  const loading = workspaceLoading
  const switchWorkspace = async (workspaceId: string) => {
    await selectWorkspace(workspaceId)
  }
  
  React.useEffect(() => {
    setMounted(true)
  }, [])

  // Show loading during SSR or when workspace is loading
  if (!mounted || loading || currentWorkspace.id === "loading") {
    return (
      <SidebarMenuButton
        role="combobox"
        className={cn("w-full justify-between", className)}
      >
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 rounded bg-muted animate-pulse" />
          <span className="text-lg">Loading...</span>
        </div>
        {state === "expanded" && (
          <ChevronsUpDown className="ml-auto h-4 w-4 shrink-0 opacity-50" />
        )}
      </SidebarMenuButton>
    )
  }

  const selectedWorkspace = workspaces.find(
    (workspace) => workspace.id === currentWorkspace.id
  ) || currentWorkspace

  return (
    <>
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <SidebarMenuButton
          role="combobox"
          aria-expanded={open}
          aria-label="Select workspace"
          className={cn("w-full justify-between", className)}
        >
          <div className="flex items-center gap-2 min-w-0 flex-1">
            {/* show larger icon */}
            <div className="text-3xl h-5 w-5 flex-shrink-0">
              {selectedWorkspace?.icon}
            </div>
            <span className="text-lg font-semibold truncate">
              {selectedWorkspace?.name}
            </span>
          </div>
          {state === "expanded" && (
            <ChevronsUpDown className="ml-auto h-4 w-4 shrink-0 opacity-50" />
          )}
        </SidebarMenuButton>
      </PopoverTrigger>
      <PopoverContent 
        className="w-[200px] p-0"
        side={isMobile ? "bottom" : "right"}
        align="end"
        sideOffset={4}
      >
        <Command>
          <CommandInput placeholder="Search workspace..." />
          <CommandList>
            <CommandEmpty>No workspace found.</CommandEmpty>
            <CommandGroup heading="Workspaces">
              {workspaces.map((workspace) => (
                <CommandItem
                  key={workspace.id}
                  value={workspace.id}
                  onSelect={(value: string) => {
                    switchWorkspace(value)
                    setOpen(false)
                  }}
                >
                  <div className="flex items-center gap-2">
                    {workspace.icon}
                    <span>{workspace.name}</span>
                  </div>
                  <Check
                    className={cn(
                      "ml-auto h-4 w-4",
                      currentWorkspace.id === workspace.id
                        ? "opacity-100"
                        : "opacity-0"
                    )}
                  />
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup>
              <CommandItem
                onSelect={() => {
                  setOpen(false)
                  // Navigate to onboarding page for new workspace creation
                  // Pass a flag to indicate this is for additional workspace
                  window.location.href = '/onboarding?additional=true'
                }}
              >
                <Plus className="mr-2 h-4 w-4" />
                Create workspace
              </CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
    </>
  )
} 