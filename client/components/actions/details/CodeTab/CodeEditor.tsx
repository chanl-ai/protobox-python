"use client"

import { useState, useEffect, useRef } from "react"
import { Editor } from "@monaco-editor/react"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { 
  Code, 
  Play, 
  Save, 
  Undo, 
  Redo, 
  Search, 
  Replace,
  Settings,
  Maximize,
  X,
  ChevronLeft,
  ChevronRight
} from "lucide-react"
interface CodeEditorProps {
  selectedFile?: string
  fileContent: string
  isModified: boolean
  isLoading: boolean
  isExplorerCollapsed: boolean
  onToggleExplorer: () => void
  onContentChange: (content: string) => void
  onSave: () => void
  canSave: boolean
}

export function CodeEditor({ 
  selectedFile, 
  fileContent, 
  isModified, 
  isLoading,
  isExplorerCollapsed, 
  onToggleExplorer, 
  onContentChange,
  onSave,
  canSave
}: CodeEditorProps) {
  const { theme } = useTheme()
  const editorRef = useRef<any>(null)

  // Force Monaco layout refresh when explorer is toggled
  useEffect(() => {
    if (editorRef.current) {
      // Small delay to allow layout to settle
      const timeoutId = setTimeout(() => {
        editorRef.current?.layout()
      }, 100)
      return () => clearTimeout(timeoutId)
    }
  }, [isExplorerCollapsed])

  const handleContentChange = (newContent: string) => {
    onContentChange(newContent)
  }

  const handleSave = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    onSave()
  }

  const handleSearch = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (editorRef.current) {
      editorRef.current.getAction('actions.find').run()
    }
  }

  const handleReplace = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (editorRef.current) {
      editorRef.current.getAction('editor.action.startFindReplaceAction').run()
    }
  }

  const handleUndo = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (editorRef.current) {
      editorRef.current.trigger('keyboard', 'undo')
    }
  }

  const handleRedo = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (editorRef.current) {
      editorRef.current.trigger('keyboard', 'redo')
    }
  }

  const handleToggleExplorer = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    onToggleExplorer()
  }

  const currentFileName = selectedFile || "src/main.js"
  const getLanguageFromFile = (filename: string) => {
    if (filename.endsWith('.py')) return 'python'
    if (filename.endsWith('.js')) return 'javascript'
    if (filename.endsWith('.ts')) return 'typescript'
    if (filename.endsWith('.json')) return 'json'
    if (filename.endsWith('.md')) return 'markdown'
    if (filename.endsWith('.html')) return 'html'
    if (filename.endsWith('.css')) return 'css'
    if (filename.endsWith('.sql')) return 'sql'
    if (filename.endsWith('.sh')) return 'shell'
    if (filename.endsWith('.yml') || filename.endsWith('.yaml')) return 'yaml'
    if (filename.endsWith('.xml')) return 'xml'
    return 'text'
  }

  const getEditorTheme = () => {
    return theme === 'dark' ? 'vs-dark' : 'light'
  }

  const handleEditorMount = (editor: any) => {
    editorRef.current = editor
    // Configure editor options for optimal experience
    editor.updateOptions({
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      automaticLayout: true,
      fontSize: 14,
      lineHeight: 20,
      wordWrap: 'on',
      tabSize: 2,
      insertSpaces: true,
      renderWhitespace: 'boundary',
      renderLineHighlight: 'line',
      cursorBlinking: 'smooth',
      smoothScrolling: true,
      folding: true,
      bracketMatching: 'always',
      autoIndent: 'advanced',
      formatOnType: true,
      formatOnPaste: true,
      suggestOnTriggerCharacters: true,
      quickSuggestions: true,
      parameterHints: { enabled: true },
      hover: { enabled: true },
      contextmenu: true,
    })
  }

  return (
    <div className="h-full flex flex-col bg-background min-w-0 overflow-hidden">
      {/* Editor Header - Compact */}
      <div className="px-3 py-2 border-b bg-muted/20 flex items-center min-h-[44px] min-w-0">
        <div className="flex items-center gap-2 min-w-0 overflow-hidden">
          {/* Explorer Toggle Button */}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 flex-shrink-0"
            onClick={handleToggleExplorer}
            title={isExplorerCollapsed ? "Show Explorer" : "Hide Explorer"}
          >
            {isExplorerCollapsed ? (
              <ChevronRight className="h-3 w-3" />
            ) : (
              <ChevronLeft className="h-3 w-3" />
            )}
          </Button>
          
          <div className="flex items-center gap-1 px-2 py-1 bg-muted rounded text-xs min-w-0">
            <Code className="h-3 w-3 flex-shrink-0" />
            <span className="font-mono text-xs truncate max-w-[120px]">{currentFileName}</span>
            {isLoading && <div className="w-3 h-3 border border-muted-foreground border-t-transparent rounded-full animate-spin flex-shrink-0" />}
            {isModified && !isLoading && <div className="w-1.5 h-1.5 bg-orange-500 rounded-full flex-shrink-0" />}
          </div>
        </div>
        
        {/* Spacer */}
        <div className="flex-1 min-w-2"></div>
        
        {/* Editor Actions - Compact - Always visible with minimum width */}
        <div className="flex items-center gap-0.5 flex-shrink-0 min-w-[280px]">
          {/* Search/Replace */}
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-7 w-7 p-0 flex-shrink-0" 
            onClick={handleSearch}
            title="Search"
          >
            <Search className="h-3 w-3" />
          </Button>
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-7 w-7 p-0 flex-shrink-0" 
            onClick={handleReplace}
            title="Replace"
          >
            <Replace className="h-3 w-3" />
          </Button>
          
          <Separator orientation="vertical" className="h-3 mx-1 flex-shrink-0" />
          
          {/* Undo/Redo */}
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-7 w-7 p-0 flex-shrink-0" 
            onClick={handleUndo}
            title="Undo"
          >
            <Undo className="h-3 w-3" />
          </Button>
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-7 w-7 p-0 flex-shrink-0" 
            onClick={handleRedo}
            title="Redo"
          >
            <Redo className="h-3 w-3" />
          </Button>
          
          <Separator orientation="vertical" className="h-3 mx-1 flex-shrink-0" />
          
          {/* Save button */}
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-7 px-2 text-xs flex-shrink-0"
            onClick={handleSave}
            disabled={!canSave || !isModified || isLoading}
            title="Save File"
          >
            <Save className="h-3 w-3 mr-1" />
            {isLoading ? "Loading..." : "Save"}
          </Button>
        </div>
      </div>

      {/* Editor Content */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-8 h-8 border-2 border-muted-foreground border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Loading file content...</p>
            </div>
          </div>
        ) : (
          <Editor
            height="100%"
            language={getLanguageFromFile(currentFileName)}
            value={fileContent}
            theme={getEditorTheme()}
            onMount={handleEditorMount}
            onChange={(value) => {
              const newValue = value || ""
              handleContentChange(newValue)
            }}
            options={{
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              automaticLayout: true,
              fontSize: 14,
              lineHeight: 20,
              wordWrap: 'on',
              tabSize: 2,
              insertSpaces: true,
              renderWhitespace: 'boundary',
              renderLineHighlight: 'line',
              cursorBlinking: 'smooth',
              smoothScrolling: true,
              lineNumbers: 'on',
              folding: true,
              bracketMatching: 'always',
              autoIndent: 'advanced',
              formatOnType: true,
              formatOnPaste: true,
              suggestOnTriggerCharacters: true,
              quickSuggestions: true,
              parameterHints: { enabled: true },
              hover: { enabled: true },
              contextmenu: true,
            }}
          />
        )}
      </div>
    </div>
  )
}