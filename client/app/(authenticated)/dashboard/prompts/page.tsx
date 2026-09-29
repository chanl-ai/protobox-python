"use client"

import { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { useWorkspaceReady } from "@/hooks/useWorkspaceReady"
import { Button } from "@/components/ui/button"
import { Plus, RefreshCw, Download, FileText, Edit, Trash2, Eye } from "lucide-react"
import { DataTablePage } from "@/components/common/data-table-page"
import { createColumns } from "@/components/prompts/columns"
import { DataTableToolbar } from "@/components/prompts/data-table-toolbar"
import { CreatePromptDialog } from "@/components/prompts/create-prompt-dialog"
import { VersionHistoryDialog } from "@/components/prompts/version-history-dialog"
import { promptsApi } from "@/lib/api/prompts"
import { toast } from "sonner"

// Initial empty state for prompts
const initialPrompts: any[] = []

export default function PromptsPage() {
  const searchParams = useSearchParams()
  const { user } = useAuth()
  const { isReady, workspaceId, getDependencies } = useWorkspaceReady()
  const [prompts, setPrompts] = useState(initialPrompts)
  const [loading, setLoading] = useState(true)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [versionHistoryOpen, setVersionHistoryOpen] = useState(false)
  const [selectedPrompt, setSelectedPrompt] = useState<any>(null)

  // Check if create dialog should be open from URL params
  useEffect(() => {
    if (searchParams.get('create') === 'true') {
      setCreateDialogOpen(true)
    }
  }, [searchParams])

  // Load prompts data
  const loadData = async () => {
    if (!workspaceId) return

    setLoading(true)
    try {
      const response = await promptsApi.listPrompts(workspaceId)
      // Transform API data to match UI expectations
      const transformedPrompts = response.prompts.map((prompt: any) => ({
        ...prompt,
        status: prompt.is_active ? 'Active' : 'Draft',
        usage_count: prompt.usage_count || 0,
        created_by: prompt.created_by || 'System',
        tags: prompt.tags || [],
        workspace_id: workspaceId
      }))
      setPrompts(transformedPrompts)
    } catch (error) {
      console.error('Failed to load prompts:', error)
      toast.error('Failed to load prompts')
      // Set empty array on error instead of keeping stale data
      setPrompts([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isReady || !workspaceId) return
    loadData()
  }, getDependencies())

  // Stats for the page
  const stats = [
    {
      title: "Total Prompts",
      value: prompts.length.toString(),
      description: "All prompts in workspace",
      icon: FileText
    },
    {
      title: "Active Prompts", 
      value: prompts.filter(p => p.status === "Active").length.toString(),
      description: "Currently active prompts",
      icon: Eye
    },
    {
      title: "Total Usage",
      value: prompts.reduce((sum, p) => sum + p.usage_count, 0).toString(),
      description: "Total times used",
      icon: RefreshCw
    },
    {
      title: "Categories",
      value: [...new Set(prompts.map(p => p.category))].length.toString(),
      description: "Unique categories",
      icon: FileText
    }
  ]

  // Handle version history
  const handleVersionHistory = (prompt: any) => {
    setSelectedPrompt(prompt)
    setVersionHistoryOpen(true)
  }

  // Create columns with version history handler
  const tableColumns = createColumns(handleVersionHistory)

  // Action handlers
  const handleRefresh = () => {
    loadData()
  }

  const handleEdit = (prompt: any) => {
    // TODO: Navigate to edit page
    toast.info(`Edit prompt: ${prompt.name}`)
  }

  const handleDelete = (prompt: any) => {
    // TODO: Show delete confirmation dialog
    toast.info(`Delete prompt: ${prompt.name}`)
  }

  const handleExport = () => {
    // TODO: Implement export functionality
    toast.info("Exporting prompts...")
  }

  const handleCreateSuccess = (newPrompt: any) => {
    setPrompts(prev => [newPrompt, ...prev])
    setCreateDialogOpen(false)
    toast.success("Prompt created successfully")
    loadData() // Reload from API
  }

  if (!isReady) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2">Initializing workspace...</span>
      </div>
    )
  }

  return (
    <DataTablePage
      pageTitle="Prompts"
      pageDescription="Manage and organize your AI prompts for better productivity"
      pageIcon={FileText}
      stats={stats}
      statsColumns={4}
      localStorageKey="prompts-analytics-visible"
      tableTitle="All Prompts"
      tableDescription="Manage your collection of AI prompts with advanced filtering and search"
      columns={tableColumns}
      data={prompts}
      toolbar={DataTableToolbar}
      headerActions={
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
          <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Create Prompt
          </Button>
        </div>
      }
    >
      <CreatePromptDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={handleCreateSuccess}
      />
      
      {selectedPrompt && (
        <VersionHistoryDialog
          open={versionHistoryOpen}
          onOpenChange={setVersionHistoryOpen}
          prompt={selectedPrompt}
          onRestore={(versionId) => {
            toast.success(`Version restored successfully`)
            loadData() // Reload prompts
          }}
        />
      )}
    </DataTablePage>
  )
}
