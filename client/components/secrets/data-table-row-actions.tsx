"use client"

import { DotsHorizontalIcon } from "@radix-ui/react-icons"
import { Row } from "@tanstack/react-table"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Secret } from "./columns"

interface DataTableRowActionsProps<TData> {
  row: Row<TData>
  onEdit?: (secret: Secret) => void
  onDelete?: (secret: Secret) => void
  onRevoke?: (secret: Secret) => void
  onRotate?: (secret: Secret) => void
  onTest?: (secret: Secret) => void
}

export function DataTableRowActions<TData>({
  row,
  onEdit,
  onDelete,
  onRevoke,
  onRotate,
  onTest,
}: DataTableRowActionsProps<TData>) {
  const secret = row.original as Secret

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
        <DropdownMenuItem onClick={() => onEdit?.(secret)}>
          Edit
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onTest?.(secret)}>
          Test Connection
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onRotate?.(secret)}>
          Rotate Key
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuSub>
          <DropdownMenuSubTrigger>Labels</DropdownMenuSubTrigger>
          <DropdownMenuSubContent>
            <DropdownMenuRadioGroup value="production">
              <DropdownMenuRadioItem value="production">
                Production
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="staging">
                Staging
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="development">
                Development
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuSubContent>
        </DropdownMenuSub>
        <DropdownMenuSeparator />
        <DropdownMenuItem 
          onClick={() => onRevoke?.(secret)}
          className="text-orange-600"
        >
          Revoke
          <DropdownMenuShortcut>⌘⌫</DropdownMenuShortcut>
        </DropdownMenuItem>
        <DropdownMenuItem 
          onClick={() => onDelete?.(secret)}
          className="text-red-600"
        >
          Delete
          <DropdownMenuShortcut>⌘⌫</DropdownMenuShortcut>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}