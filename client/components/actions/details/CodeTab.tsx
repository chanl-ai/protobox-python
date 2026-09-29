"use client"

import { useState, useRef, useEffect } from "react"
import { useParams } from "next/navigation"
import { useWorkspaceReady } from "@/hooks"
import { useActionCodeFiles } from "@/hooks/useActionCodeFiles"
import { CodeExplorer } from "./CodeTab/CodeExplorer"
import { CodeEditor } from "./CodeTab/CodeEditor"
import { CodeFooter } from "./CodeTab/CodeFooter"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, Upload, Loader2, Rocket } from "lucide-react"
import { toast } from "sonner"
import { useActionForm } from "./FormProvider"

interface ResizablePanelProps {
  children: React.ReactNode
  minWidth?: number
  maxWidth?: number
  defaultWidth?: number
  onWidthChange?: (width: number) => void
}

function ResizablePanel({ 
  children, 
  minWidth = 200, 
  maxWidth = 500, 
  defaultWidth = 300,
  onWidthChange 
}: ResizablePanelProps) {
  const [width, setWidth] = useState(defaultWidth)
  const [isResizing, setIsResizing] = useState(false)
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !panelRef.current) return
      
      const rect = panelRef.current.getBoundingClientRect()
      const newWidth = e.clientX - rect.left
      const clampedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth))
      
      setWidth(clampedWidth)
      onWidthChange?.(clampedWidth)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing, minWidth, maxWidth, onWidthChange])

  return (
    <div className="flex h-full">
      <div 
        ref={panelRef}
        style={{ width }}
        className="flex-shrink-0"
      >
        {children}
      </div>
      <div
        className="w-1 bg-border hover:bg-blue-500 cursor-ew-resize transition-colors"
        onMouseDown={() => setIsResizing(true)}
      />
    </div>
  )
}

export function CodeTab() {
  const params = useParams()
  const { workspaceId } = useWorkspaceReady()
  const { action } = useActionForm()
  const actionId = params.actionId as string

  const [selectedFile, setSelectedFile] = useState<string>("")
  const [isExplorerCollapsed, setIsExplorerCollapsed] = useState(false)
  const [currentFileContent, setCurrentFileContent] = useState<string>("")
  const [currentLine, setCurrentLine] = useState(1)
  const [currentColumn, setCurrentColumn] = useState(1)

  // Use the new file management hook
  const {
    files,
    loading,
    deploying,
    error,
    loadFileContent,
    saveFile,
    updateFileContent,
    getFile,
    isFileDirty,
    hasUnsavedChanges,
    refreshFiles,
    deployAction,
  } = useActionCodeFiles(workspaceId, actionId)

  // Early return if action is not loaded or not a CODE_RUN action
  if (!action || action.type !== 'CODE_RUN') {
    return (
      <div className="h-[calc(100vh-200px)] border rounded-lg overflow-hidden bg-card flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">
            {!action ? 'Loading action...' : 'This action is not a CODE_RUN type'}
          </p>
        </div>
      </div>
    )
  }

  // Auto-select first file when files load
  useEffect(() => {
    if (files.length > 0 && !selectedFile) {
      // Try to find main file, otherwise use first file
      const mainFile = files.find(f => 
        f.filename.includes('main.') || 
        f.filename === 'main.js' || 
        f.filename === 'main.py'
      ) || files[0]
      
      setSelectedFile(mainFile.filename)
    }
  }, [files, selectedFile])

  // Load file content when selected file changes
  useEffect(() => {
    if (selectedFile && workspaceId && actionId) {
      const file = getFile(selectedFile)
      
      // If file content is already loaded, use it immediately
      if (file && file.content) {
        setCurrentFileContent(file.content)
      } else {
        // Clear current content and load new file
        setCurrentFileContent('')
        
        // Always load content for files without content
        loadFileContent(selectedFile).then(content => {
          setCurrentFileContent(content)
        }).catch(error => {
          console.error('Failed to load file content:', error)
          setCurrentFileContent('')
        })
      }
    }
  }, [selectedFile, workspaceId, actionId])

  // Sync currentFileContent when the file content is updated in the files state
  useEffect(() => {
    if (selectedFile) {
      const file = getFile(selectedFile)
      if (file && file.content && !file.isLoading) {
        setCurrentFileContent(file.content)
      }
    }
  }, [files, selectedFile, getFile])

  const handleFileSelect = (filename: string) => {
    setSelectedFile(filename)
  }

  const handleContentChange = (content: string) => {
    if (selectedFile) {
      setCurrentFileContent(content)
      updateFileContent(selectedFile, content)
    }
  }

  const handleSave = async () => {
    if (selectedFile && currentFileContent) {
      await saveFile(selectedFile, currentFileContent)
    }
  }

  const handleToggleExplorer = () => {
    setIsExplorerCollapsed(!isExplorerCollapsed)
  }

  const handleFileUploaded = async (filename: string) => {
    // Force a refresh of the files state
    await refreshFiles()
    // Auto-select the newly uploaded file
    setSelectedFile(filename)
  }

  if (loading) {
    return (
      <div className="h-[calc(100vh-200px)] border rounded-lg overflow-hidden bg-card flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading files...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-[calc(100vh-200px)] border rounded-lg overflow-hidden bg-card flex items-center justify-center">
        <div className="text-center">
          <p className="text-destructive mb-4">{error}</p>
          <Button onClick={() => window.location.reload()}>
            Reload
          </Button>
        </div>
      </div>
    )
  }

  const currentFile = getFile(selectedFile)
  // File is loading if it's explicitly marked as loading
  const currentFileIsLoading = Boolean(currentFile?.isLoading)
  const currentFileIsDirty = selectedFile ? isFileDirty(selectedFile) : false
  const unsavedFilesCount = files.filter(f => f.isDirty).length
  const actionConfig = action.default_config as any
  const language = actionConfig?.language || 'javascript'

  return (
    <div className="h-[calc(100vh-200px)] border rounded-lg overflow-hidden bg-card">
      {/* Main Editor Area */}
      <div className="h-full flex flex-col">
        <div className="flex-1 flex overflow-hidden">
          {!isExplorerCollapsed && (
            <ResizablePanel defaultWidth={240} minWidth={180} maxWidth={400}>
              <div className="h-full border-r bg-muted/20">
                <CodeExplorer 
                  workspaceId={workspaceId!}
                  actionId={actionId}
                  onFileSelect={handleFileSelect}
                  selectedFile={selectedFile}
                  onFileUploaded={handleFileUploaded}
                />
              </div>
            </ResizablePanel>
          )}
          
          {/* Code Editor Panel */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {/* Code Tab Header */}
            <div className="flex items-center justify-between p-3 border-b bg-background">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-medium">Code Editor</h3>
                {unsavedFilesCount > 0 && (
                  <span className="text-xs text-muted-foreground">
                    ({unsavedFilesCount} unsaved file{unsavedFilesCount !== 1 ? 's' : ''})
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  onClick={deployAction}
                  disabled={deploying || loading}
                  className="h-8"
                >
                  {deploying ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Deploying...
                    </>
                  ) : (
                    <>
                      <Rocket className="h-4 w-4 mr-2" />
                      Deploy
                    </>
                  )}
                </Button>
              </div>
            </div>
            
            <CodeEditor 
              selectedFile={selectedFile}
              fileContent={currentFileContent}
              isModified={currentFileIsDirty}
              isLoading={currentFileIsLoading}
              isExplorerCollapsed={isExplorerCollapsed}
              onToggleExplorer={handleToggleExplorer}
              onContentChange={handleContentChange}
              onSave={handleSave}
              canSave={!currentFileIsLoading}
            />
          </div>
        </div>
        
        {/* Footer - Status Bar */}
          <CodeFooter 
            selectedFile={selectedFile}
          isModified={currentFileIsDirty}
          language={language}
          lineCount={currentFileContent ? currentFileContent.split('\n').length : 0}
          currentLine={currentLine}
          currentColumn={currentColumn}
          unsavedFilesCount={unsavedFilesCount}
          isConnected={!error}
          timeout={actionConfig?.timeout || 30}
        />
      </div>
    </div>
  )
}