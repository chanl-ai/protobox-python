"use client"

import { Cross2Icon } from "@radix-ui/react-icons"
import { Table } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { DataTableViewOptions } from "../knowledge-base/data-table-view-options"
import { DataTableFacetedFilter } from "../knowledge-base/data-table-faceted-filter"
import {
  Workflow,
  Play,
  Pause,
  AlertCircle,
  Clock,
} from "lucide-react"

export const workflowStatuses = [
  {
    value: "active",
    label: "Active",
    icon: Play,
  },
  {
    value: "inactive",
    label: "Inactive",
    icon: Pause,
  },
  {
    value: "error",
    label: "Error",
    icon: AlertCircle,
  },
  {
    value: "scheduled",
    label: "Scheduled",
    icon: Clock,
  },
]

export const workflowTypes = [
  {
    value: "automation",
    label: "Automation",
    icon: Workflow,
  },
  {
    value: "data-sync",
    label: "Data Sync",
    icon: Workflow,
  },
  {
    value: "notification",
    label: "Notification",
    icon: Workflow,
  },
  {
    value: "reporting",
    label: "Reporting",
    icon: Workflow,
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
          placeholder="Filter workflows..."
          value={(table.getColumn("name")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("name")?.setFilterValue(event.target.value)
          }
          className="h-8 w-[150px] lg:w-[250px]"
        />
        {table.getColumn("status") && (
          <DataTableFacetedFilter
            column={table.getColumn("status")}
            title="Status"
            options={workflowStatuses}
          />
        )}
        {table.getColumn("tags") && (
          <DataTableFacetedFilter
            column={table.getColumn("tags")}
            title="Type"
            options={workflowTypes}
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
