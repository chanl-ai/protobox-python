"use client"

import { ReactNode } from "react"
import { useParams } from "next/navigation"
import { useWorkspaceReady } from "@/hooks"
import { useAction, type Action } from "@/lib/api/hooks"
import { ActionHeader } from "@/components/actions/details/ActionHeader"
import { TabNavigation } from "@/components/actions/details/TabNavigation"
import { FormProvider } from "@/components/actions/details/FormProvider"
import { TestingSidebar } from "@/components/actions/details/TestingSidebar"
import { Loader2 } from "lucide-react"
import { toast } from "sonner"

interface ActionDetailsLayoutProps {
  children: ReactNode
}

export default function ActionDetailsLayout({ children }: ActionDetailsLayoutProps) {
  const params = useParams()
  const { workspaceId } = useWorkspaceReady()
  const actionId = params.actionId as string

  // Load action data using hook
  const { data: action, isLoading: loading, error } = useAction(workspaceId || undefined, actionId)

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

  return (
    <FormProvider action={action}>
      <div className="space-y-6">
        {/* Header with action info and buttons */}
        <ActionHeader action={action} />
        
        {/* Smart tab navigation based on action type */}
        <TabNavigation actionType={action.type} actionId={actionId} />

        {/* Main content area */}
        <div className="grid grid-cols-12 gap-6">
          {/* Form content (left column) */}
          <div className="col-span-8">
            {children}
          </div>

          {/* Testing sidebar (right column) */}
          <div className="col-span-4">
            <TestingSidebar action={action} />
          </div>
        </div>
      </div>
    </FormProvider>
  )
}