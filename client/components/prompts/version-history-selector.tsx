"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import { History, ChevronDown } from "lucide-react"
import { promptsApi } from "@/lib/api/prompts"

interface VersionHistorySelectorProps {
  workspaceId: string
  promptId: string
  currentVersion?: number
  onVersionSelect: (version: number) => void
  onViewFullHistory: () => void
}

interface PromptVersion {
  version: number
  change_summary: string
  created_at: string
  created_by: string
}

export function VersionHistorySelector({
  workspaceId,
  promptId,
  currentVersion,
  onVersionSelect,
  onViewFullHistory
}: VersionHistorySelectorProps) {
  const [versions, setVersions] = useState<PromptVersion[]>([])
  const [loading, setLoading] = useState(false)
  const [latestVersion, setLatestVersion] = useState<number>(1)

  useEffect(() => {
    const loadVersions = async () => {
      if (!workspaceId || !promptId) return
      
      setLoading(true)
      try {
        const response = await promptsApi.getPromptVersions(workspaceId, promptId)
        setVersions(response.versions)
        setLatestVersion(response.current_version)
      } catch (error) {
        console.error('Failed to load versions:', error)
      } finally {
        setLoading(false)
      }
    }

    loadVersions()
  }, [workspaceId, promptId])

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString()
    } catch {
      return "Unknown"
    }
  }

  const selectedVersion = currentVersion || latestVersion
  const selectedVersionData = versions.find(v => v.version === selectedVersion)
  const isLatestVersion = selectedVersion === latestVersion

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" disabled={loading}>
          <History className="h-4 w-4 mr-2" />
          <span className="flex items-center gap-2">
            v{selectedVersion}
            {isLatestVersion && <Badge variant="secondary" className="text-xs px-1">Current</Badge>}
            <ChevronDown className="h-3 w-3" />
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel className="flex items-center justify-between">
          Version History
          <Button
            variant="ghost"
            size="sm"
            onClick={onViewFullHistory}
            className="text-xs"
          >
            View All
          </Button>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        {loading ? (
          <DropdownMenuItem disabled>
            Loading versions...
          </DropdownMenuItem>
        ) : versions.length === 0 ? (
          <DropdownMenuItem disabled>
            No versions available
          </DropdownMenuItem>
        ) : (
          versions.slice(0, 5).map((version) => (
            <DropdownMenuItem
              key={version.version}
              onClick={() => onVersionSelect(version.version)}
              className={`flex items-center justify-between p-2 ${
                selectedVersion === version.version ? 'bg-muted' : ''
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="font-medium">v{version.version}</span>
                {version.version === latestVersion && (
                  <Badge variant="secondary" className="text-xs px-1">Current</Badge>
                )}
              </div>
            </DropdownMenuItem>
          ))
        )}
        
        {versions.length > 5 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onViewFullHistory}>
              <span className="text-sm text-muted-foreground">
                View {versions.length - 5} more versions...
              </span>
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}