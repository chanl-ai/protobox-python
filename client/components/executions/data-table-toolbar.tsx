"use client"

import { Cross2Icon } from "@radix-ui/react-icons"
import { Table } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { DataTableViewOptions } from "../knowledge-base/data-table-view-options"
import { DataTableFacetedFilter } from "../knowledge-base/data-table-faceted-filter"
import { DateRangePickerWithPresets } from "@/components/ui/date-range-picker"
import { DateRange } from "react-day-picker"
import {
  Play,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
} from "lucide-react"

export const executionStatuses = [
  {
    value: "pending",
    label: "Pending",
    icon: Clock,
  },
  {
    value: "running",
    label: "Running",
    icon: Play,
  },
  {
    value: "completed",
    label: "Completed",
    icon: CheckCircle,
  },
  {
    value: "failed",
    label: "Failed",
    icon: XCircle,
  },
  {
    value: "cancelled",
    label: "Cancelled",
    icon: AlertCircle,
  },
]

interface DataTableToolbarProps<TData> {
  table: Table<TData>
  dateRange?: DateRange
  onDateRangeChange?: (range: DateRange | undefined) => void
}

export function DataTableToolbar<TData>({
  table,
  dateRange,
  onDateRangeChange,
}: DataTableToolbarProps<TData>) {
  const isFiltered = table.getState().columnFilters.length > 0
  const hasDateFilter = dateRange?.from || dateRange?.to

  return (
    <div className="flex items-center justify-between">
      <div className="flex flex-1 items-center space-x-2">
        <Input
          placeholder="Filter executions..."
          value={(table.getColumn("action_name")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("action_name")?.setFilterValue(event.target.value)
          }
          className="h-8 w-[150px] lg:w-[250px]"
        />
        {table.getColumn("status") && (
          <DataTableFacetedFilter
            column={table.getColumn("status")}
            title="Status"
            options={executionStatuses}
          />
        )}
        <DateRangePickerWithPresets
          value={dateRange}
          onChange={onDateRangeChange}
          placeholder="Filter by date range"
        />
        {(isFiltered || hasDateFilter) && (
          <Button
            variant="ghost"
            onClick={() => {
              table.resetColumnFilters()
              onDateRangeChange?.(undefined)
            }}
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