"use client"

import { useState, useEffect } from "react"
import { useWorkspaceReady } from "@/hooks"
import { auditApi } from "@/lib/api/audit"
import { AuditLog } from "@/lib/types/audit"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { 
  FileText, 
  Download,
  RefreshCw,
  Loader2,
  Activity,
  TrendingUp,
  Shield,
  Users
} from "lucide-react"

import { DataTablePage } from "@/components/common/data-table-page"
import { columns } from "@/components/audit-logs/columns"
import { DataTableRowActions } from "@/components/audit-logs/data-table-row-actions"
import { DataTableToolbar } from "@/components/audit-logs/data-table-toolbar"

export default function AuditLogsPage() {
  const { isReady, workspaceId, user, getDependencies } = useWorkspaceReady()
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 50,
  })
  const [total, setTotal] = useState(0)

  // Load audit logs
  const loadData = async () => {
    if (!isReady) return
    
    try {
      // Calculate date range for last 7 days
      const endDate = new Date()
      const startDate = new Date()
      startDate.setDate(startDate.getDate() - 7)

      const auditLogsResponse = await auditApi.getLogs(workspaceId!, {
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
        limit: pagination.pageSize,
        offset: pagination.pageIndex * pagination.pageSize
      })
      
      if (auditLogsResponse.data?.logs) {
        setAuditLogs(auditLogsResponse.data.logs)
        setTotal(auditLogsResponse.data.total || auditLogsResponse.data.logs.length)
      }
    } catch (error) {
      toast.error('Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [...getDependencies(), pagination.pageIndex, pagination.pageSize])

  // Row action handlers
  const handleViewDetails = (auditLog: AuditLog) => {
    toast.success('Viewing audit log details')
  }

  const handleExport = (auditLog: AuditLog) => {
    toast.success('Exporting audit log entry')
  }

  const handleViewRelated = (auditLog: AuditLog) => {
    toast.success('Viewing related audit logs')
  }

  const handleRefresh = () => {
    setLoading(true)
    loadData()
  }

  const handleExportAll = () => {
    toast.success('Exporting all audit logs')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading audit logs...</span>
      </div>
    )
  }

  // Transform audit logs to match the new type structure
  const transformedAuditLogs: AuditLog[] = auditLogs.map(log => ({
    id: log.id,
    timestamp: log.timestamp,
    user_id: log.user_id,
    user_name: log.user_name,
    action: log.action,
    resource_type: log.resource_type as "user" | "workspace" | "action" | "secret" | "execution" | "audit_log",
    resource_id: log.resource_id,
    ip_address: log.ip_address,
    user_agent: log.user_agent,
    status: log.status as "success" | "failure" | "warning",
    details: log.details,
    workspace_id: log.workspace_id,
  }))

  const stats = [
    { 
      title: "Total Events", 
      value: auditLogs.length.toString(), 
      description: "Last 7 days",
      icon: FileText
    },
    { 
      title: "Success Rate", 
      value: auditLogs.length > 0 ? `${Math.round((auditLogs.filter(l => l.status === "success").length / auditLogs.length) * 100)}%` : "0%", 
      description: "Successful operations",
      icon: TrendingUp
    },
    { 
      title: "Security Events", 
      value: auditLogs.filter(l => l.action.includes("auth") || l.action.includes("login") || l.resource_type === "secret").length.toString(), 
      description: "Auth & secrets",
      icon: Shield
    },
    { 
      title: "Active Users", 
      value: new Set(auditLogs.map(l => l.user_id)).size.toString(), 
      description: "Unique users",
      icon: Users
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
            onExport={handleExport}
            onViewRelated={handleViewRelated}
          />
        ),
      }
    }
    return col
  })

  return (
    <DataTablePage
      pageTitle="Audit Logs"
      pageDescription="Monitor and track all activities and security events"
      pageIcon={FileText}
      stats={stats}
      statsColumns={4}
      localStorageKey="audit-logs-analytics-visible"
      tableTitle="Activity Log"
      tableDescription="Complete audit trail of all user and system activities"
      columns={enhancedColumns}
      data={transformedAuditLogs}
      toolbar={DataTableToolbar}
      headerActions={
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportAll}>
            <Download className="w-4 h-4 mr-2" />
            Export All
          </Button>
        </div>
      }
    />
  )
}