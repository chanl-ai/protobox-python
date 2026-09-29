"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Checkbox } from "@/components/ui/checkbox"
import { Badge } from "@/components/ui/badge"
import { DataTableColumnHeader } from "../common/data-table-column-header"
import { DataTableRowActions } from "./data-table-row-actions"
import { Key, Shield, Lock, Unlock } from "lucide-react"

export type Secret = {
  id: string
  name: string
  description?: string
  secret_type: string
  tags?: string[]
  is_active: boolean
  created_at: string
  updated_at: string
  expires_at?: string
  usage_count: number
  max_usage_count?: number
}

const getTypeIcon = (type: string) => {
  switch (type) {
    case "api_key":
      return <Key className="h-4 w-4 text-blue-500" />
    case "oauth":
      return <Shield className="h-4 w-4 text-green-500" />
    case "password":
      return <Lock className="h-4 w-4 text-orange-500" />
    case "certificate":
      return <Unlock className="h-4 w-4 text-purple-500" />
    default:
      return <Key className="h-4 w-4 text-gray-500" />
  }
}

const getStatusBadge = (status: string) => {
  switch (status) {
    case "active":
      return <Badge variant="default" className="bg-green-500">Active</Badge>
    case "inactive":
      return <Badge variant="secondary">Inactive</Badge>
    case "expired":
      return <Badge variant="destructive">Expired</Badge>
    case "revoked":
      return <Badge variant="secondary">Revoked</Badge>
    case "pending":
      return <Badge variant="outline">Pending</Badge>
    default:
      return <Badge variant="outline">{status}</Badge>
  }
}

export const columns: ColumnDef<Secret>[] = [
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
    accessorKey: "name",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Name" />
    ),
    cell: ({ row }) => {
      return (
        <div className="flex space-x-2">
          <span className="max-w-[500px] truncate font-medium">
            {row.getValue("name")}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "secret_type",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Type" />
    ),
    cell: ({ row }) => {
      const type = row.original.secret_type
      return (
        <div className="flex items-center space-x-2">
          {getTypeIcon(type)}
          <span className="capitalize">{type.replace("_", " ")}</span>
        </div>
      )
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id))
    },
  },
  {
    accessorKey: "is_active",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Status" />
    ),
    cell: ({ row }) => {
      const isActive = row.original.is_active
      const status = isActive ? "active" : "inactive"
      return getStatusBadge(status)
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id))
    },
  },
  {
    accessorKey: "expires_at",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Expires" />
    ),
    cell: ({ row }) => {
      const expires_at = row.getValue("expires_at") as string
      if (!expires_at) {
        return <span className="text-muted-foreground">Never</span>
      }
      const date = new Date(expires_at)
      const now = new Date()
      const isExpired = date < now
      
      return (
        <span className={isExpired ? "text-red-500" : ""}>
          {date.toLocaleDateString()}
        </span>
      )
    },
  },
  {
    accessorKey: "last_accessed",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Last Accessed" />
    ),
    cell: ({ row }) => {
      const last_accessed = row.getValue("last_accessed") as string
      if (!last_accessed) {
        return <span className="text-muted-foreground">Never</span>
      }
      return new Date(last_accessed).toLocaleDateString()
    },
  },
  {
    id: "actions",
    cell: ({ row }) => <DataTableRowActions row={row} />,
  },
]