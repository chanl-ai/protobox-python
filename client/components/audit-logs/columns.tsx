"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { DataTableColumnHeader } from "../common/data-table-column-header"
import { DataTableRowActions } from "./data-table-row-actions"
import { 
  User, 
  Settings, 
  Database, 
  Key, 
  Play, 
  FileText, 
  AlertTriangle, 
  Info, 
  CheckCircle 
} from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { AuditLog } from "@/lib/types/audit"

const getResourceIcon = (resourceType: string) => {
  switch (resourceType) {
    case "user":
      return <User className="h-4 w-4 text-blue-500" />
    case "workspace":
      return <Settings className="h-4 w-4 text-purple-500" />
    case "action":
      return <Play className="h-4 w-4 text-green-500" />
    case "secret":
      return <Key className="h-4 w-4 text-orange-500" />
    case "execution":
      return <Database className="h-4 w-4 text-indigo-500" />
    case "audit_log":
      return <FileText className="h-4 w-4 text-gray-500" />
    default:
      return <FileText className="h-4 w-4 text-gray-500" />
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case "success":
      return <CheckCircle className="h-4 w-4 text-green-500" />
    case "failure":
      return <AlertTriangle className="h-4 w-4 text-red-500" />
    case "warning":
      return <Info className="h-4 w-4 text-yellow-500" />
    default:
      return <Info className="h-4 w-4 text-gray-500" />
  }
}

const getStatusBadge = (status: string) => {
  switch (status) {
    case "success":
      return <Badge variant="default" className="bg-green-500">Success</Badge>
    case "failure":
      return <Badge variant="destructive">Failure</Badge>
    case "warning":
      return <Badge variant="outline" className="text-yellow-600 border-yellow-600">Warning</Badge>
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}

export const columns: ColumnDef<AuditLog>[] = [
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
    accessorKey: "timestamp",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Timestamp" />
    ),
    cell: ({ row }) => {
      const timestamp = row.getValue("timestamp") as string
      return (
        <div className="flex flex-col">
          <span className="text-sm">
            {formatDistanceToNow(new Date(timestamp), { addSuffix: true })}
          </span>
          <span className="text-xs text-muted-foreground">
            {new Date(timestamp).toLocaleString()}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "user_name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="User" />
    ),
    cell: ({ row }) => {
      const userName = row.getValue("user_name") as string
      const userId = row.original.user_id
      return (
        <div className="flex items-center space-x-2">
          <User className="h-4 w-4 text-muted-foreground" />
          <span className="max-w-[200px] truncate font-medium">
            {userName || userId}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "action",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Action" />
    ),
    cell: ({ row }) => {
      return (
        <div className="flex space-x-2">
          <span className="max-w-[300px] truncate font-medium">
            {row.getValue("action")}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "resource_type",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Resource" />
    ),
    cell: ({ row }) => {
      const resourceType = row.original.resource_type
      return (
        <div className="flex items-center space-x-2">
          {getResourceIcon(resourceType)}
          <span className="capitalize">{resourceType.replace("_", " ")}</span>
        </div>
      )
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id))
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
    accessorKey: "ip_address",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="IP Address" />
    ),
    cell: ({ row }) => {
      const ipAddress = row.getValue("ip_address") as string
      return ipAddress ? (
        <span className="text-sm font-mono">{ipAddress}</span>
      ) : (
        <span className="text-muted-foreground">-</span>
      )
    },
  },
  {
    id: "actions",
    cell: ({ row }) => <DataTableRowActions row={row} />,
  },
]