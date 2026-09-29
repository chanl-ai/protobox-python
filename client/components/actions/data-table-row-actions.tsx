"use client"

import { DotsHorizontalIcon } from "@radix-ui/react-icons"
import { Row } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Play, Edit, Trash2, Copy, CheckCircle } from "lucide-react"
import type { Action } from "@/lib/api/hooks"

interface DataTableRowActionsProps {
  row: Row<Action>
  onExecute?: (action: Action) => void
  onValidate?: (action: Action) => void
  onEdit?: (action: Action) => void
  onDelete?: (action: Action) => void
  onDuplicate?: (action: Action) => void
}

export function DataTableRowActions({
  row,
  onExecute,
  onValidate,
  onEdit,
  onDelete,
  onDuplicate,
}: DataTableRowActionsProps) {
  const action = row.original
  const isAdminAction = !action.id || action.type === 'ADMIN'

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
        {!isAdminAction && (
          <>
            <DropdownMenuItem onClick={() => onExecute?.(action)}>
              <Play className="mr-2 h-4 w-4" />
              Execute
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onValidate?.(action)}>
              <CheckCircle className="mr-2 h-4 w-4" />
              Validate
            </DropdownMenuItem>
          </>
        )}
        <DropdownMenuItem onClick={() => onEdit?.(action)}>
          <Edit className="mr-2 h-4 w-4" />
          {isAdminAction ? 'View Info' : 'Edit'}
        </DropdownMenuItem>
        {!isAdminAction && (
          <>
            <DropdownMenuItem onClick={() => onDuplicate?.(action)}>
              <Copy className="mr-2 h-4 w-4" />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={() => onDelete?.(action)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}