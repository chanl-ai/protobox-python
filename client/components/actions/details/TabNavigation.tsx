"use client"

import { useRouter, usePathname } from "next/navigation"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Action } from "@/lib/api/hooks"

type ActionType = Action['type']

interface TabNavigationProps {
  actionType: ActionType
  actionId: string
}

export function TabNavigation({ actionType, actionId }: TabNavigationProps) {
  const router = useRouter()
  const pathname = usePathname()
  
  // Determine current tab from pathname
  const getCurrentTab = () => {
    if (pathname.includes('/general')) return 'general'
    if (pathname.includes('/rest')) return 'rest'
    if (pathname.includes('/code')) return 'code'
    return 'general' // default
  }

  const handleTabChange = (value: string) => {
    router.push(`/dashboard/actions/${actionId}/details/${value}`)
  }

  // Define available tabs based on action type
  const getAvailableTabs = () => {
    const tabs = [
      { value: 'general', label: 'General', enabled: true }
    ]

    if (actionType === 'REST') {
      tabs.push({ value: 'rest', label: 'REST Configuration', enabled: true })
    } else if (actionType === 'CODE_RUN') {
      tabs.push({ value: 'code', label: 'Code Editor', enabled: true })
    }

    return tabs
  }

  const availableTabs = getAvailableTabs()
  const currentTab = getCurrentTab()

  return (
    <div className="border-b">
      <Tabs value={currentTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="h-12 p-1 grid w-full" style={{ gridTemplateColumns: `repeat(${availableTabs.length}, 1fr)` }}>
          {availableTabs.map((tab) => (
            <TabsTrigger 
              key={tab.value}
              value={tab.value}
              disabled={!tab.enabled}
              className="h-10 text-sm font-medium data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
            >
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
    </div>
  )
}