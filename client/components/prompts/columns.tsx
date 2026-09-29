"use client"

import { ColumnDef } from "@tanstack/react-table"
import { useRouter } from "next/navigation"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { MoreHorizontal, Eye, Edit, Trash2, Copy, Archive, History } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

export type Prompt = {
  id: string
  name: string
  description: string
  category: string
  status: "Active" | "Draft" | "Archived"
  created_at: string
  updated_at: string
  usage_count: number
  tags: string[]
  created_by: string
  version?: number
}

export const createColumns = (onVersionHistory?: (prompt: Prompt) => void): ColumnDef<Prompt>[] => [
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
    header: "Name",
    cell: ({ row }) => {
      const prompt = row.original
      const router = useRouter()
      
      const handleNameClick = () => {
        router.push(`/dashboard/prompts/${prompt.id}/edit`)
      }
      
      return (
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <button
              onClick={handleNameClick}
              className="font-medium text-left hover:text-primary hover:underline cursor-pointer"
            >
              {prompt.name}
            </button>
            {prompt.version && (
              <Badge variant="outline" className="text-xs">
                v{prompt.version}
              </Badge>
            )}
          </div>
          <div className="text-sm text-muted-foreground line-clamp-2">
            {prompt.description}
          </div>
        </div>
      )
    },
  },
  {
    accessorKey: "category",
    header: "Category",
    cell: ({ row }) => {
      const category = row.getValue("category") as string
      return (
        <Badge variant="secondary" className="font-medium">
          {category}
        </Badge>
      )
    },
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const status = row.getValue("status") as string
      const variant = status === "Active" ? "default" : 
                    status === "Draft" ? "secondary" : "outline"
      return (
        <Badge variant={variant}>
          {status}
        </Badge>
      )
    },
  },
  {
    accessorKey: "usage_count",
    header: "Usage",
    cell: ({ row }) => {
      const count = row.getValue("usage_count") as number
      return (
        <div className="text-right font-medium">
          {count.toLocaleString()}
        </div>
      )
    },
  },
  {
    accessorKey: "created_by",
    header: "Created By",
    cell: ({ row }) => {
      const createdBy = row.getValue("created_by") as string
      return (
        <div className="text-sm text-muted-foreground">
          {createdBy}
        </div>
      )
    },
  },
  {
    accessorKey: "updated_at",
    header: "Last Updated",
    cell: ({ row }) => {
      const updatedAt = row.getValue("updated_at") as string
      return (
        <div className="text-sm text-muted-foreground">
          {formatDistanceToNow(new Date(updatedAt), { addSuffix: true })}
        </div>
      )
    },
  },
  {
    id: "actions",
    cell: ({ row }) => {
      const prompt = row.original
      const router = useRouter()

      const handleEdit = () => {
        router.push(`/dashboard/prompts/${prompt.id}/edit`)
      }

      return (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 p-0">
              <span className="sr-only">Open menu</span>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>Actions</DropdownMenuLabel>
            <DropdownMenuItem
              onClick={() => navigator.clipboard.writeText(prompt.id)}
            >
              <Copy className="mr-2 h-4 w-4" />
              Copy ID
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Eye className="mr-2 h-4 w-4" />
              View Details
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onVersionHistory?.(prompt)}>
              <History className="mr-2 h-4 w-4" />
              Version History
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleEdit}>
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <Archive className="mr-2 h-4 w-4" />
              Archive
            </DropdownMenuItem>
            <DropdownMenuItem className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )
    },
  },
]

// For backward compatibility
export const columns = createColumns()
