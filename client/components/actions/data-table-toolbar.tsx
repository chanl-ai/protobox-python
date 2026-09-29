"use client"

import { Cross2Icon } from "@radix-ui/react-icons"
import { Table } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { DataTableViewOptions } from "../knowledge-base/data-table-view-options"
import { DataTableFacetedFilter } from "../knowledge-base/data-table-faceted-filter"
import {
  Globe,
  Database,
  Code,
  Bot,
  Workflow,
  Shield,
} from "lucide-react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"

export const actionTypes = [
  {
    value: "REST",
    label: "REST API",
    icon: Globe,
  },
  {
    value: "DATABASE",
    label: "Database",
    icon: Database,
  },
  {
    value: "CODE_RUN",
    label: "Code Run",
    icon: Code,
  },
  {
    value: "O3",
    label: "AI Assistant",
    icon: Bot,
  },
  {
    value: "WORKFLOW",
    label: "Workflow",
    icon: Workflow,
  },
  {
    value: "ADMIN",
    label: "Admin Tool",
    icon: Shield,
  },
]

export const statuses = [
  {
    value: "active",
    label: "Active",
  },
  {
    value: "inactive",
    label: "Inactive",
  },
  {
    value: "error",
    label: "Error",
  },
]

interface DataTableToolbarProps<TData> {
  table: Table<TData>
  showAdminActions?: boolean
  onShowAdminActionsChange?: (value: boolean) => void
}

export function DataTableToolbar<TData>({
  table,
  showAdminActions = false,
  onShowAdminActionsChange,
}: DataTableToolbarProps<TData>) {
  const isFiltered = table.getState().columnFilters.length > 0

  return (
    <div className="flex items-center justify-between">
      <div className="flex flex-1 items-center space-x-2">
        <Input
          placeholder="Filter actions..."
          value={(table.getColumn("name")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("name")?.setFilterValue(event.target.value)
          }
          className="h-8 w-[150px] lg:w-[250px]"
        />
        {table.getColumn("type") && (
          <DataTableFacetedFilter
            column={table.getColumn("type")}
            title="Type"
            options={actionTypes}
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
        {onShowAdminActionsChange && (
          <div className="flex items-center space-x-2 ml-2">
            <Switch
              id="show-admin"
              checked={showAdminActions}
              onCheckedChange={onShowAdminActionsChange}
            />
            <Label htmlFor="show-admin" className="text-sm font-normal">
              Show admin tools
            </Label>
          </div>
        )}
      </div>
      <DataTableViewOptions table={table} />
    </div>
  )
}