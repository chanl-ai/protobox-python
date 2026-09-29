"use client"

import { useState, useMemo } from "react"
import { useWorkspaceReady } from "@/hooks"
import { useExecutions, type Execution } from "@/lib/api/hooks"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { toast } from "sonner"
import { DateRange } from "react-day-picker"
import { 
  Play, 
  RefreshCw,
  Pause,
  Loader2,
  Activity,
  TrendingUp,
  Clock,
  CheckCircle
} from "lucide-react"

import { DataTablePage } from "@/components/common/data-table-page"
import { columns, type Execution as ExecutionType } from "@/components/executions/columns"
import { DataTableRowActions } from "@/components/executions/data-table-row-actions"
import { DataTableToolbar } from "@/components/executions/data-table-toolbar"

export default function ExecutionsPage() {
  const { workspaceId, isReady } = useWorkspaceReady()
  const [dateRange, setDateRange] = useState<DateRange | undefined>(undefined)

  // Prepare parameters with date filtering using useMemo
  const params = useMemo(() => {
    const p: { 
      limit?: number;
      start_date?: string; 
      end_date?: string;
    } = {
      limit: 20, // Default limit for initial load
    }

    // Add date filtering if range is selected
    if (dateRange?.from) {
      p.start_date = dateRange.from.toISOString()
    }
    if (dateRange?.to) {
      // Set end time to end of day
      const endDate = new Date(dateRange.to)
      endDate.setHours(23, 59, 59, 999)
      p.end_date = endDate.toISOString()
    }

    return p
  }, [dateRange])

  // Use hook to load executions
  const { data: executions, isLoading: loading, error, refetch } = useExecutions(workspaceId || undefined, params)

  // Handle date range changes - just update state, hook will refetch automatically
  const handleDateRangeChange = (range: DateRange | undefined) => {
    setDateRange(range)
  }

  // Row action handlers
  const handleViewDetails = (execution: ExecutionType) => {
    toast.success('Viewing execution details')
  }

  const handleRetry = (execution: ExecutionType) => {
    toast.success('Execution retried')
  }

  const handleCancel = (execution: ExecutionType) => {
    toast.success('Execution cancelled')
  }

  const handleViewOutput = (execution: ExecutionType) => {
    toast.success('Viewing execution output')
  }

  const handleRefresh = () => {
    refetch()
  }

  const handlePauseAll = () => {
    toast.success('All executions paused')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading executions...</span>
      </div>
    )
  }

  // Transform executions to match the component type structure  
  const transformedExecutions: ExecutionType[] = (executions || []).map(execution => ({
    id: execution.id,
    action_id: execution.action_id,
    action_name: execution.action_name || execution.action_id,
    status: execution.status as "pending" | "running" | "completed" | "failed" | "cancelled",
    started_at: execution.started_at,
    completed_at: execution.completed_at,
    duration: execution.execution_time_ms || execution.duration_ms,
    error_message: execution.error_message || execution.error,
    result: execution.output_data || execution.output,
    triggered_by: execution.user_name || execution.user_id || 'Unknown',
    workspace_id: execution.workspace_id,
  }))

  const stats = [
    { 
      title: "Total Executions", 
      value: (executions?.length || 0).toString(), 
      description: `${(executions || []).filter(e => e.status === "completed").length} completed`,
      icon: Play
    },
    { 
      title: "Success Rate", 
      value: executions && executions.length > 0 ? `${Math.round(((executions || []).filter(e => e.status === "completed").length / executions.length) * 100)}%` : "0%", 
      description: "Last 30 days",
      icon: CheckCircle
    },
    { 
      title: "Currently Running", 
      value: (executions || []).filter(e => e.status === "running").length.toString(), 
      description: "Active now",
      icon: Activity
    },
    { 
      title: "Failed Today", 
      value: (executions || []).filter(e => e.status === "failed").length.toString(), 
      description: "Needs attention",
      icon: TrendingUp
    },
  ]

  // Enhance columns with row actions
  const enhancedColumns = columns.map(col => {
    if (col.id === 'actions') {
      return {
        ...col,
        cell: ({ row }: any) => (
          <DataTableRowActions
            row={row}
            onViewDetails={handleViewDetails}
            onRetry={handleRetry}
            onCancel={handleCancel}
            onViewOutput={handleViewOutput}
          />
        ),
      }
    }
    return col
  })

  return (
    <DataTablePage
      pageTitle="Executions"
      pageDescription="Monitor and track action executions in real-time"
      pageIcon={Play}
      stats={stats}
      statsColumns={4}
      localStorageKey="executions-analytics-visible"
      tableTitle="Execution History"
      tableDescription="Recent action executions with detailed information"
      columns={enhancedColumns}
      data={transformedExecutions}
      toolbar={(props) => (
        <DataTableToolbar 
          {...props} 
          dateRange={dateRange}
          onDateRangeChange={handleDateRangeChange}
        />
      )}
      headerActions={
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handlePauseAll}>
            <Pause className="w-4 h-4 mr-2" />
            Pause All
          </Button>
        </div>
      }
    />
  )
}