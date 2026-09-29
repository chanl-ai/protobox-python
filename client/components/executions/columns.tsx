"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { DataTableColumnHeader } from "../common/data-table-column-header"
import { DataTableRowActions } from "./data-table-row-actions"
import { Play, CheckCircle, XCircle, Clock, AlertCircle } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

export type Execution = {
  id: string
  action_id: string
  action_name?: string
  status: "pending" | "running" | "completed" | "failed" | "cancelled"
  started_at: string
  completed_at?: string
  duration?: number
  error_message?: string
  result?: any
  triggered_by: string
  workspace_id: string
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case "completed":
      return <CheckCircle className="h-4 w-4 text-green-500" />
    case "failed":
      return <XCircle className="h-4 w-4 text-red-500" />
    case "running":
      return <Play className="h-4 w-4 text-blue-500" />
    case "pending":
      return <Clock className="h-4 w-4 text-yellow-500" />
    case "cancelled":
      return <AlertCircle className="h-4 w-4 text-gray-500" />
    default:
      return <Clock className="h-4 w-4 text-gray-500" />
  }
}

const getStatusBadge = (status: string) => {
  switch (status) {
    case "completed":
      return <Badge variant="default" className="bg-green-500">Completed</Badge>
    case "failed":
      return <Badge variant="destructive">Failed</Badge>
    case "running":
      return <Badge variant="default" className="bg-blue-500">Running</Badge>
    case "pending":
      return <Badge variant="outline">Pending</Badge>
    case "cancelled":
      return <Badge variant="secondary">Cancelled</Badge>
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}

export const columns: ColumnDef<Execution>[] = [
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={
          table.getIsAllPageRowsSelected() ||
          (table.getIsSomePageRowsSelected() && "indeterminate")
        }
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label="Select all"
        className="translate-y-[2px]"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label="Select row"
        className="translate-y-[2px]"
      />
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "action_name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Action" />
    ),
    cell: ({ row }) => {
      return (
        <div className="flex space-x-2">
          <span className="max-w-[500px] truncate font-medium">
            {row.getValue("action_name") || row.original.action_id}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "status",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Status" />
    ),
    cell: ({ row }) => {
      const status = row.original.status
      return (
        <div className="flex items-center space-x-2">
          {getStatusIcon(status)}
          {getStatusBadge(status)}
        </div>
      )
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id))
    },
  },
  {
    accessorKey: "started_at",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Started" />
    ),
    cell: ({ row }) => {
      const startedAt = row.getValue("started_at") as string
      
      // Handle null, undefined, or invalid date strings
      if (!startedAt) {
        return <span className="text-muted-foreground">-</span>
      }
      
      const date = new Date(startedAt)
      
      // Check if the date is valid
      if (isNaN(date.getTime())) {
        return <span className="text-muted-foreground">Invalid date</span>
      }
      
      return (
        <div className="flex flex-col">
          <span className="text-sm">
            {formatDistanceToNow(date, { addSuffix: true })}
          </span>
          <span className="text-xs text-muted-foreground">
            {date.toLocaleString()}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "duration",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Duration" />
    ),
    cell: ({ row }) => {
      const duration = row.getValue("duration") as number
      const status = row.original.status
      
      if (!duration && status === "running") {
        const startedAtStr = row.original.started_at
        if (!startedAtStr) {
          return <span className="text-muted-foreground">-</span>
        }
        
        const startedAt = new Date(startedAtStr)
        if (isNaN(startedAt.getTime())) {
          return <span className="text-muted-foreground">-</span>
        }
        
        const now = new Date()
        const runningDuration = Math.floor((now.getTime() - startedAt.getTime()) / 1000)
        return <span className="text-sm text-blue-600">{runningDuration}s (running)</span>
      }
      
      if (!duration) {
        return <span className="text-muted-foreground">-</span>
      }
      
      return <span className="text-sm">{duration}s</span>
    },
  },
  {
    accessorKey: "triggered_by",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Triggered By" />
    ),
    cell: ({ row }) => {
      const triggeredBy = row.getValue("triggered_by") as string
      return (
        <div className="flex space-x-2">
          <span className="max-w-[200px] truncate text-sm">
            {triggeredBy}
          </span>
        </div>
      )
    },
  },
  {
    id: "actions",
    cell: ({ row }) => <DataTableRowActions row={row} />,
  },
]