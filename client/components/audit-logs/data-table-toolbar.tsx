"use client"

import { Cross2Icon } from "@radix-ui/react-icons"
import { Table } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { DataTableViewOptions } from "../knowledge-base/data-table-view-options"
import { DataTableFacetedFilter } from "../knowledge-base/data-table-faceted-filter"
import {
  User,
  Settings,
  Database,
  Key,
  Play,
  FileText,
  CheckCircle,
  AlertTriangle,
  Info,
} from "lucide-react"

export const resourceTypes = [
  {
    value: "user",
    label: "User",
    icon: User,
  },
  {
    value: "workspace",
    label: "Workspace",
    icon: Settings,
  },
  {
    value: "action",
    label: "Action",
    icon: Play,
  },
  {
    value: "secret",
    label: "Secret",
    icon: Key,
  },
  {
    value: "execution",
    label: "Execution",
    icon: Database,
  },
  {
    value: "audit_log",
    label: "Audit Log",
    icon: FileText,
  },
]

export const statuses = [
  {
    value: "success",
    label: "Success",
    icon: CheckCircle,
  },
  {
    value: "failure",
    label: "Failure",
    icon: AlertTriangle,
  },
  {
    value: "warning",
    label: "Warning",
    icon: Info,
  },
]

interface DataTableToolbarProps<TData> {
  table: Table<TData>
}

export function DataTableToolbar<TData>({
  table,
}: DataTableToolbarProps<TData>) {
  const isFiltered = table.getState().columnFilters.length > 0

  return (
    <div className="flex items-center justify-between">
      <div className="flex flex-1 items-center space-x-2">
        <Input
          placeholder="Filter audit logs..."
          value={(table.getColumn("action")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("action")?.setFilterValue(event.target.value)
          }
          className="h-8 w-[150px] lg:w-[250px]"
        />
        {table.getColumn("resource_type") && (
          <DataTableFacetedFilter
            column={table.getColumn("resource_type")}
            title="Resource"
            options={resourceTypes}
          />
        )}
        {table.getColumn("status") && (
          <DataTableFacetedFilter
            column={table.getColumn("status")}
            title="Status"
            options={statuses}
          />
        )}
        {isFiltered && (
          <Button
            variant="ghost"
            onClick={() => table.resetColumnFilters()}
            className="h-8 px-2 lg:px-3"
          >
            Reset
            <Cross2Icon className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
      <DataTableViewOptions table={table} />
    </div>
  )
}