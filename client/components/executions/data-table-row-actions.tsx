"use client"

import { DotsHorizontalIcon } from "@radix-ui/react-icons"
import { Row } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Execution } from "./columns"

interface DataTableRowActionsProps<TData> {
  row: Row<TData>
  onViewDetails?: (execution: Execution) => void
  onRetry?: (execution: Execution) => void
  onCancel?: (execution: Execution) => void
  onViewOutput?: (execution: Execution) => void
}

export function DataTableRowActions<TData>({
  row,
  onViewDetails,
  onRetry,
  onCancel,
  onViewOutput,
}: DataTableRowActionsProps<TData>) {
  const execution = row.original as Execution

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="flex h-8 w-8 p-0 data-[state=open]:bg-muted"
        >
          <DotsHorizontalIcon className="h-4 w-4" />
          <span className="sr-only">Open menu</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[160px]">
        <DropdownMenuItem onClick={() => onViewDetails?.(execution)}>
          View Details
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onViewOutput?.(execution)}>
          View Output
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {execution.status === "failed" && (
          <DropdownMenuItem onClick={() => onRetry?.(execution)}>
            Retry
            <DropdownMenuShortcut>⌘R</DropdownMenuShortcut>
          </DropdownMenuItem>
        )}
        {(execution.status === "pending" || execution.status === "running") && (
          <DropdownMenuItem 
            onClick={() => onCancel?.(execution)}
            className="text-red-600"
          >
            Cancel
            <DropdownMenuShortcut>⌘⌫</DropdownMenuShortcut>
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}