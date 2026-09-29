"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { DataTableColumnHeader } from "../common/data-table-column-header"
import { DataTableRowActions } from "./data-table-row-actions"
import {
  Globe,
  Database,
  Code,
  Bot,
  Workflow,
  Settings,
  Shield,
} from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import type { Action } from "@/lib/api/hooks"
import Link from "next/link"

const getTypeIcon = (type: string) => {
  switch (type) {
    case "REST":
      return <Globe className="h-4 w-4 text-muted-foreground" />
    case "DATABASE":
      return <Database className="h-4 w-4 text-muted-foreground" />
    case "CODE_RUN":
      return <Code className="h-4 w-4 text-muted-foreground" />
    case "O3":
      return <Bot className="h-4 w-4 text-muted-foreground" />
    case "WORKFLOW":
      return <Workflow className="h-4 w-4 text-muted-foreground" />
    case "ADMIN":
      return <Shield className="h-4 w-4 text-muted-foreground" />
    default:
      return <Settings className="h-4 w-4 text-muted-foreground" />
  }
}

const getStatusVariant = (
  status: string
): "default" | "secondary" | "destructive" | "outline" => {
  switch (status) {
    case "active":
      return "default"
    case "inactive":
      return "secondary"
    case "error":
      return "destructive"
    default:
      return "outline"
  }
}

export const columns: ColumnDef<Action>[] = [
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
      <DataTableColumnHeader column={column} title="Name & Description" />
    ),
    cell: ({ row }) => {
      const type = row.original.type
      const actionId = row.original.id
      const description = row.original.description

      // Ensure we never create links with null/undefined IDs
      const isValidActionId = actionId && actionId !== 'null' && actionId !== 'undefined'
      const isAdminAction = type === "ADMIN" || !isValidActionId

      return (
        <div className="flex items-start space-x-2 max-w-md">
          <span className="mt-0.5 flex-shrink-0">{getTypeIcon(type)}</span>
          <div className="min-w-0 flex-1">
            {!isAdminAction ? (
              <Link
                href={`/dashboard/actions/${actionId}`}
                className="font-medium hover:underline block w-full text-left"
              >
                {row.getValue("name")}
              </Link>
            ) : (
              <button
                className="font-medium block w-full text-left hover:underline cursor-pointer text-foreground"
                onClick={() => {
                  // We'll handle this with a data attribute and event delegation
                  const event = new CustomEvent('admin-action-click', {
                    detail: row.original
                  })
                  document.dispatchEvent(event)
                }}
              >
                {row.getValue("name")}
              </button>
            )}
            <div className="text-sm text-muted-foreground mt-1 line-clamp-2">
              {description || "No description"}
            </div>
          </div>
        </div>
      )
    },
  },
  {
    accessorKey: "type",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Type" />
    ),
    cell: ({ row }) => {
      const type = row.getValue("type") as string
      const typeLabels: Record<string, string> = {
        REST: "REST API",
        DATABASE: "Database",
        CODE_RUN: "Code Run",
        O3: "AI Assistant",
        WORKFLOW: "Workflow",
        ADMIN: "Admin Tool",
      }
      return (
        <div className="flex w-[120px] items-center">
          <Badge variant="outline">
            {typeLabels[type] || type}
          </Badge>
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
      const status = row.getValue("status") as string
      return (
        <div className="flex w-[100px] items-center">
          <Badge variant={getStatusVariant(status)} className="capitalize">
            {status}
          </Badge>
        </div>
      )
    },
    filterFn: (row, id, value) => {
      return value.includes(row.getValue(id))
    },
  },
  {
    accessorKey: "version",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Version" />
    ),
    cell: ({ row }) => {
      const version = row.getValue("version") as string
      return (
        <div className="flex w-[80px] items-center">
          <span className="text-sm text-muted-foreground">
            {version || "1.0.0"}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Created" />
    ),
    cell: ({ row }) => {
      const date = row.getValue("created_at")
      if (!date) return null
      
      return (
        <div className="flex w-[120px] items-center">
          <span className="text-sm text-muted-foreground">
            {formatDistanceToNow(new Date(date as string), { addSuffix: true })}
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