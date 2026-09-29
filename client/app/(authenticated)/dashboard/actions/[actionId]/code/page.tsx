"use client"

import { useParams, useRouter } from "next/navigation"
import { useWorkspaceReady } from "@/hooks"
import { useAction, type Action } from "@/lib/api/hooks"
import { ActionHeader } from "@/components/actions/details/ActionHeader"
import { FormProvider } from "@/components/actions/details/FormProvider"
import { TestingSidebar } from "@/components/actions/details/TestingSidebar"
import { CodeTab } from "@/components/actions/details/CodeTab"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

export default function ActionCodePage() {
  const params = useParams()
  const router = useRouter()
  const { isReady, workspaceId } = useWorkspaceReady()
  const actionId = params.actionId as string

  // Load action data using hook
  const { data: action, isLoading: loading, error } = useAction(workspaceId || undefined, actionId)

  // Redirect non-CODE_RUN actions to general tab
  if (action && action.type !== 'CODE_RUN') {
    router.replace(`/dashboard/actions/${actionId}`)
    return null
  }

  if (error) {
    toast.error('Failed to load action')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading action...</p>
        </div>
      </div>
    )
  }

  if (!action) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-muted-foreground">Action not found</p>
        </div>
      </div>
    )
  }

  const availableTabs = [
    { value: 'general', label: 'General', href: `/dashboard/actions/${actionId}`, active: false },
    { value: 'code', label: 'Code Editor', href: `/dashboard/actions/${actionId}/code`, active: true }
  ]

  return (
    <FormProvider action={action}>
      <div className="space-y-6">
        {/* Header with action info and buttons */}
        <ActionHeader action={action} />
        
        {/* Main content area with left column and right sidebar */}
        <div className="grid grid-cols-12 gap-6">
          {/* Left Column - Form content with tabs */}
          <div className="col-span-8">
            <Tabs value="code" className="w-full">
              {/* Natural width tabs - not full width */}
              <TabsList className="inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground mb-6">
                {availableTabs.map((tab) => (
                  <TabsTrigger
                    key={tab.value}
                    value={tab.value}
                    onClick={() => router.push(tab.href)}
                    data-state={tab.active ? 'active' : 'inactive'}
                    className="inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm cursor-pointer"
                  >
                    {tab.label}
                  </TabsTrigger>
                ))}
              </TabsList>

              {/* Tab Content - Always show Code tab since this is the code page */}
              <TabsContent value="code" className="space-y-6">
                <CodeTab />
              </TabsContent>
            </Tabs>
          </div>

          {/* Right Column - Testing sidebar */}
          <div className="col-span-4">
            <TestingSidebar action={action} />
          </div>
        </div>
      </div>
    </FormProvider>
  )
}