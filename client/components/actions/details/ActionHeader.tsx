"use client"

import { Action } from "@/lib/api/hooks"
import { Button } from "@/components/ui/button"
import { Globe, Database, Code, BookOpen, Settings, Save, Zap, Loader2, Rocket, FileText } from "lucide-react"
import { useFormContext } from "react-hook-form"
import { useRouter } from "next/navigation"

const actionTypeIcons = {
  REST: Globe,
  DATABASE: Database,
  CODE_RUN: Code,
  KNOWLEDGE_BASE: BookOpen,
}

interface ActionHeaderProps {
  action: Action
  onSave?: () => void
  onTest?: () => void
  saving?: boolean
  testing?: boolean
}

export function ActionHeader({ 
  action, 
  onSave, 
  onTest, 
  saving = false, 
  testing = false 
}: ActionHeaderProps) {
  const form = useFormContext()
  const router = useRouter()
  const Icon = actionTypeIcons[action.type as keyof typeof actionTypeIcons] || Settings

  const handleViewLogs = () => {
    router.push(`/dashboard/actions/${action.id}/logs`)
  }
  
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <Icon className="h-8 w-8 text-muted-foreground" />
        <div>
          <h1 className="text-3xl font-bold">
            {action && form?.watch("method") && action.type === "REST" 
              ? `[${form.watch("method")}] ${action.name}`
              : action?.name || "Edit Action"
            }
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Configure your action settings and test its functionality
          </p>
        </div>
      </div>
      
      <div className="flex items-center space-x-2">
        {/* Deploy and View Logs buttons */}
        <Button onClick={handleViewLogs} variant="outline" size="sm">
          <FileText className="mr-2 h-4 w-4" />
          View Logs
        </Button>

        {onTest && (
          <Button onClick={onTest} disabled={testing} variant="outline">
            {testing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <Zap className="mr-2 h-4 w-4" />
                Test Action
              </>
            )}
          </Button>
        )}
        
        {onSave && (
          <Button onClick={onSave} disabled={saving}>
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Save Action
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  )
}