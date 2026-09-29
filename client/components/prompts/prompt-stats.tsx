"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { BarChart3, Calendar, User, FileText } from "lucide-react"

interface PromptStatsProps {
  usageCount: number
  status: string
  createdAt: string
  createdBy: string
  updatedAt: string
}

export function PromptStats({
  usageCount = 0,
  status = "Draft",
  createdAt = "",
  createdBy = "Unknown",
  updatedAt = ""
}: PromptStatsProps) {
  const formatDate = (dateString: string) => {
    if (!dateString) return "Unknown"
    try {
      return new Date(dateString).toLocaleDateString()
    } catch {
      return "Unknown"
    }
  }

  const getStatusVariant = (status: string) => {
    return status === "Active" ? "default" : "secondary"
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Usage Statistics
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Total Usage</span>
          <span className="font-semibold">{usageCount.toLocaleString()}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Status</span>
          <Badge variant={getStatusVariant(status)}>
            {status}
          </Badge>
        </div>
        <Separator />
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Calendar className="h-4 w-4" />
            <span>Created {formatDate(createdAt)}</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <User className="h-4 w-4" />
            <span>By {createdBy}</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <FileText className="h-4 w-4" />
            <span>Last updated {formatDate(updatedAt)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}