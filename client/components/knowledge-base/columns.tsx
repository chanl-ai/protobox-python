"use client"

import { ColumnDef } from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { DataTableColumnHeader } from "./data-table-column-header"
import { DataTableRowActions } from "./data-table-row-actions"
import {
  FileText,
  Globe,
  Plug,
  Type,
  File,
  FileSpreadsheet,
  Folder,
} from "lucide-react"
import { formatDistanceToNow } from "date-fns"

// Define the data source type
export type DataSource = {
  id: string
  name: string
  type: "document" | "webpage" | "integration" | "text"
  status: "indexed" | "processing" | "synced" | "syncing" | "failed"
  size?: string
  chunks?: number
  lastUpdated: Date
  metadata?: {
    fileType?: string
    url?: string
    domain?: string
    pages?: number
    itemCount?: number
    syncSchedule?: string
    charCount?: number
  }
}

const getTypeIcon = (type: string, fileType?: string) => {
  if (type === "document") {
    switch (fileType) {
      case "pdf":
        return <FileText className="h-4 w-4" />
      case "docx":
      case "doc":
        return <File className="h-4 w-4" />
      case "xlsx":
      case "xls":
        return <FileSpreadsheet className="h-4 w-4" />
      default:
        return <File className="h-4 w-4" />
    }
  }
  switch (type) {
    case "webpage":
      return <Globe className="h-4 w-4" />
    case "integration":
      return <Plug className="h-4 w-4" />
    case "text":
      return <Type className="h-4 w-4" />
    default:
      return <File className="h-4 w-4" />
  }
}

const getStatusVariant = (
  status: string
): "default" | "secondary" | "destructive" | "outline" => {
  switch (status) {
    case "indexed":
    case "synced":
      return "default"
    case "processing":
    case "syncing":
      return "secondary"
    case "failed":
      return "destructive"
    default:
      return "outline"
  }
}

export const columns: ColumnDef<DataSource>[] = [
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
      const type = row.original.type
      const fileType = row.original.metadata?.fileType
      const url = row.original.metadata?.url
      const domain = row.original.metadata?.domain

      return (
        <div className="flex items-center space-x-2">
          <span className="text-muted-foreground">
            {getTypeIcon(type, fileType)}
          </span>
          <span className="max-w-[500px] truncate font-medium">
            {domain ? (
              <>
                {row.original.metadata?.pages && (
                  <Folder className="inline h-3 w-3 mr-1" />
                )}
                {domain}
              </>
            ) : url ? (
              url
            ) : (
              row.getValue("name")
            )}
          </span>
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
      return (
        <div className="flex w-[100px] items-center">
          <Badge variant="outline" className="capitalize">
            {type}
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
    id: "details",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Details" />
    ),
    cell: ({ row }) => {
      const source = row.original
      let details = ""

      switch (source.type) {
        case "document":
          details = source.size
            ? `${source.size} • ${source.chunks || 0} chunks`
            : "Processing..."
          break
        case "webpage":
          if (source.metadata?.pages) {
            details = `${source.metadata.pages} pages indexed`
          } else {
            details = "Single page"
          }
          break
        case "integration":
          details = source.metadata?.itemCount
            ? `${source.metadata.itemCount} items • ${source.metadata.syncSchedule}`
            : "Configuring..."
          break
        case "text":
          details = source.metadata?.charCount
            ? `${source.metadata.charCount} characters`
            : "No content"
          break
      }

      return (
        <div className="flex space-x-2">
          <span className="max-w-[200px] truncate text-sm text-muted-foreground">
            {details}
          </span>
        </div>
      )
    },
  },
  {
    accessorKey: "lastUpdated",
    header: ({ column }) => (
      <DataTableColumnHeader column={column} title="Last Updated" />
    ),
    cell: ({ row }) => {
      const date = row.getValue("lastUpdated") as Date
      return (
        <div className="flex w-[120px] items-center">
          <span className="text-sm text-muted-foreground">
            {formatDistanceToNow(date, { addSuffix: true })}
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