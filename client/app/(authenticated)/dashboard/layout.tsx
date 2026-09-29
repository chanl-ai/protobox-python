"use client"

import { useAuthStore } from "@/lib/auth/stores/auth.store"
import { DashboardPageSkeleton } from "@/components/dashboard-skeleton"
import { WorkspaceSelectionPrompt } from "@/components/workspace-selection-prompt"
import React from "react"

interface DashboardLayoutProps {
  children: React.ReactNode
}

/**
 * Dashboard Layout with Workspace Guard
 * 
 * Ensures all dashboard pages receive a guaranteed valid workspace.
 * Handles loading and error states at the layout level so individual
 * pages don't need to check workspace state.
 */
export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const { currentWorkspace, workspaceLoading: loading, error, workspaces } = useAuthStore()

  // Show loading skeleton while workspace is loading
  if (loading) {
    return <DashboardPageSkeleton />
  }

  // Show error or workspace selection if no valid workspace
  if (error || !currentWorkspace) {
    return (
      <WorkspaceSelectionPrompt 
        error={error} 
        hasWorkspaces={workspaces.length > 0} 
      />
    )
  }

  // All dashboard pages now receive guaranteed valid workspace
  return (
    <>
      {children}
    </>
  )
}