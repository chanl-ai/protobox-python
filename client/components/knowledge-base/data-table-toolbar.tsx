"use client"

import { Cross2Icon } from "@radix-ui/react-icons"
import { Table } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { DataTableViewOptions } from "./data-table-view-options"
import { DataTableFacetedFilter } from "./data-table-faceted-filter"
import {
  FileText,
  Globe,
  Plug,
  Type,
} from "lucide-react"

export const sourceTypes = [
  {
    value: "document",
    label: "Document",
    icon: FileText,
  },
  {
    value: "webpage",
    label: "Web Page",
    icon: Globe,
  },
  {
    value: "integration",
    label: "Integration",
    icon: Plug,
  },
  {
    value: "text",
    label: "Text",
    icon: Type,
  },
]

export const statuses = [
  {
    value: "indexed",
    label: "Indexed",
  },
  {
    value: "processing",
    label: "Processing",
  },
  {
    value: "synced",
    label: "Synced",
  },
  {
    value: "syncing",
    label: "Syncing",
  },
  {
    value: "failed",
    label: "Failed",
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
          placeholder="Filter sources..."
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
            options={sourceTypes}
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