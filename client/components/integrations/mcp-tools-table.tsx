"use client"

import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { CheckCircle2, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"

export interface MCPTool {
  template_id: string
  name: string
  description: string
  category: string
  enabled: boolean
  action_id?: string
}

interface MCPToolsTableProps {
  tools: MCPTool[]
  enabledTools: Record<string, boolean>
  onToggleTool: (toolId: string) => void | Promise<void>
  loading?: boolean
  error?: string | null
  className?: string
}

export function MCPToolsTable({
  tools,
  enabledTools,
  onToggleTool,
  loading = false,
  error = null,
  className
}: MCPToolsTableProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading tools...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-800">{error}</p>
      </div>
    )
  }

  if (tools.length === 0) {
    return (
      <div className="rounded-lg border border-muted bg-muted/10 p-8 text-center">
        <p className="text-sm text-muted-foreground">
          No tools available for this integration.
        </p>
      </div>
    )
  }

  return (
    <div className={cn("rounded-lg border", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[60%]">Tool</TableHead>
            <TableHead className="w-[20%] text-center">Status</TableHead>
            <TableHead className="w-[20%] text-center">Enable</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tools.map((tool) => (
            <TableRow key={tool.template_id}>
              <TableCell>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="space-y-1">
                        <div className="font-medium truncate">
                          {tool.name}
                        </div>
                        <div className="text-xs text-muted-foreground truncate max-w-[24rem]">
                          {tool.description}
                        </div>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-md">
                      <div className="space-y-2">
                        <p className="font-medium">{tool.name}</p>
                        <p className="text-sm">{tool.description}</p>
                        <p className="text-xs text-muted-foreground">
                          ID: {tool.template_id}
                        </p>
                      </div>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </TableCell>
              <TableCell className="text-center">
                {enabledTools[tool.template_id] ? (
                  <Badge variant="default" className="gap-1 text-xs">
                    <CheckCircle2 className="h-3 w-3" />
                    Active
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">Inactive</Badge>
                )}
              </TableCell>
              <TableCell className="text-center">
                <Switch
                  checked={enabledTools[tool.template_id]}
                  onCheckedChange={() => onToggleTool(tool.template_id)}
                  disabled={loading}
                  className="data-[state=checked]:bg-primary"
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}