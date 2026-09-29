"use client"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { 
  AlertCircle, 
  CheckCircle, 
  Clock, 
  Zap, 
  Settings,
  GitBranch,
  Users,
  Wifi
} from "lucide-react"

interface CodeFooterProps {
  selectedFile?: string
  isModified?: boolean
  language?: string
  lineCount?: number
  currentLine?: number
  currentColumn?: number
  executionTime?: number
  hasErrors?: boolean
  errorCount?: number
  warningCount?: number
  unsavedFilesCount?: number
  isConnected?: boolean
  timeout?: number
}

export function CodeFooter({ 
  selectedFile = "main.js",
  isModified = false,
  language = "javascript",
  lineCount = 0,
  currentLine = 1,
  currentColumn = 1,
  executionTime,
  hasErrors = false,
  errorCount = 0,
  warningCount = 0,
  unsavedFilesCount = 0,
  isConnected = true,
  timeout = 30
}: CodeFooterProps) {

  return (
    <div className="h-6 bg-muted/30 border-t flex items-center justify-between px-3 text-xs">
      {/* Left Section - File & Language Info */}
      <div className="flex items-center gap-3">
        {/* File Status */}
        <div className="flex items-center gap-1">
          {isModified ? (
            <div className="w-2 h-2 bg-orange-500 rounded-full" />
          ) : (
            <div className="w-2 h-2 bg-green-500 rounded-full" />
          )}
          <span className="font-mono text-muted-foreground">
            {selectedFile}
          </span>
        </div>

        <Separator orientation="vertical" className="h-4" />

        {/* Language */}
        <Badge variant="secondary" className="h-5 px-2 text-xs">
          {language.toUpperCase()}
        </Badge>

        {/* Line Info */}
        <span className="text-muted-foreground">
          Ln {currentLine}, Col {currentColumn}
        </span>

        {lineCount > 0 && (
          <span className="text-muted-foreground">
            ({lineCount} lines)
          </span>
        )}
      </div>

      {/* Center Section - Status & Errors */}
      <div className="flex items-center gap-3">
        {/* Error/Warning Count */}
        {(errorCount > 0 || warningCount > 0) && (
          <>
            {errorCount > 0 && (
              <div className="flex items-center gap-1 text-red-500">
                <AlertCircle className="h-3 w-3" />
                <span>{errorCount} error{errorCount !== 1 ? 's' : ''}</span>
              </div>
            )}
            
            {warningCount > 0 && (
              <div className="flex items-center gap-1 text-yellow-500">
                <AlertCircle className="h-3 w-3" />
                <span>{warningCount} warning{warningCount !== 1 ? 's' : ''}</span>
              </div>
            )}
          </>
        )}

        {/* Execution Status */}
        {executionTime !== undefined && (
          <div className="flex items-center gap-1 text-green-500">
            <CheckCircle className="h-3 w-3" />
            <span>Executed in {executionTime}ms</span>
          </div>
        )}

        {/* Unsaved Files Indicator */}
        {unsavedFilesCount > 0 && (
          <div className="flex items-center gap-1 text-orange-500">
            <AlertCircle className="h-3 w-3" />
            <span>{unsavedFilesCount} unsaved file{unsavedFilesCount !== 1 ? 's' : ''}</span>
          </div>
        )}

        {/* Connection Status */}
        <div className={`flex items-center gap-1 ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
          <Wifi className="h-3 w-3" />
          <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
        </div>
      </div>

      {/* Right Section - Settings & Actions */}
      <div className="flex items-center gap-3">
        {/* Execution Timeout */}
        <div className="flex items-center gap-1 text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>Timeout: {timeout}s</span>
        </div>

        <Separator orientation="vertical" className="h-4" />

        {/* Version Control */}
        <div className="flex items-center gap-1 text-muted-foreground">
          <GitBranch className="h-3 w-3" />
          <span>main</span>
        </div>

        {/* Collaboration */}
        <div className="flex items-center gap-1 text-muted-foreground">
          <Users className="h-3 w-3" />
          <span>1</span>
        </div>

        {/* Settings */}
        <Button variant="ghost" size="sm" className="h-5 w-5 p-0">
          <Settings className="h-3 w-3" />
        </Button>

        {/* Performance */}
        <div className="flex items-center gap-1 text-green-500">
          <Zap className="h-3 w-3" />
          <span>98%</span>
        </div>
      </div>
    </div>
  )
}