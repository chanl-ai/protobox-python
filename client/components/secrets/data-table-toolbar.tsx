"use client"

import { Cross2Icon } from "@radix-ui/react-icons"
import { Table } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { DataTableViewOptions } from "../knowledge-base/data-table-view-options"
import { DataTableFacetedFilter } from "../knowledge-base/data-table-faceted-filter"
import {
  Key,
  Shield,
  Lock,
  Unlock,
} from "lucide-react"

export const secretTypes = [
  {
    value: "api_key",
    label: "API Key",
    icon: Key,
  },
  {
    value: "oauth",
    label: "OAuth",
    icon: Shield,
  },
  {
    value: "password",
    label: "Password",
    icon: Lock,
  },
  {
    value: "certificate",
    label: "Certificate",
    icon: Unlock,
  },
]

export const statuses = [
  {
    value: true,
    label: "Active",
  },
  {
    value: false,
    label: "Inactive",
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
          placeholder="Filter secrets..."
          value={(table.getColumn("name")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("name")?.setFilterValue(event.target.value)
          }
          className="h-8 w-[150px] lg:w-[250px]"
        />
        {table.getColumn("secret_type") && (
          <DataTableFacetedFilter
            column={table.getColumn("secret_type")}
            title="Type"
            options={secretTypes}
          />
        )}
        {table.getColumn("is_active") && (
          <DataTableFacetedFilter
            column={table.getColumn("is_active")}
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