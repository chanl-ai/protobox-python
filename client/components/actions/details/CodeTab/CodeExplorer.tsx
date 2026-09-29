"use client"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { 
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { 
  File, 
  FileText, 
  Settings, 
  Play, 
  Package,
  Plus,
  Search,
  Upload,
  Trash2,
  FilePlus
} from "lucide-react"
import { useActionCodeFiles } from "@/hooks/useActionCodeFiles"
import { toast } from "sonner"

interface CodeExplorerProps {
  workspaceId: string
  actionId: string
  onFileSelect?: (filename: string) => void
  selectedFile?: string
  onFileUploaded?: (filename: string) => void
}

export function CodeExplorer({ workspaceId, actionId, onFileSelect, selectedFile, onFileUploaded }: CodeExplorerProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [isNewFileDialogOpen, setIsNewFileDialogOpen] = useState(false)
  const [newFileName, setNewFileName] = useState("")
  const [isCreatingFile, setIsCreatingFile] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const {
    files,
    fileMetadata,
    loading,
    uploadFile,
    deleteFile,
    refreshFiles,
  } = useActionCodeFiles(workspaceId, actionId)

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // Check file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        toast.error("File size must be less than 10MB")
        return
      }
      
      try {
        await uploadFile(file)
        // Refresh the file list to ensure state is synchronized
        await refreshFiles()
        // Notify parent that a file was uploaded
        onFileUploaded?.(file.name)
      } catch (error) {
        console.error('File upload failed:', error)
      }
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDeleteFile = async (filename: string) => {
    if (confirm(`Are you sure you want to delete "${filename}"?`)) {
      await deleteFile(filename)
    }
  }

  const handleCreateFile = async () => {
    if (!newFileName.trim()) {
      toast.error("Please enter a file name")
      return
    }

    // Basic filename validation
    const filename = newFileName.trim()
    
    // Check for invalid characters
    if (!/^[a-zA-Z0-9._-]+$/.test(filename)) {
      toast.error("File name can only contain letters, numbers, dots, hyphens, and underscores")
      return
    }

    // Check if file already exists
    if (files.some(f => f.filename === filename)) {
      toast.error(`File "${filename}" already exists`)
      return
    }

    // Check file extension for supported types
    const extension = filename.split('.').pop()?.toLowerCase()
    const supportedExtensions = ['js', 'mjs', 'py', 'json', 'txt', 'md', 'html', 'css', 'yml', 'yaml', 'toml']
    
    if (!extension || !supportedExtensions.includes(extension)) {
      toast.error(`Unsupported file extension. Supported: ${supportedExtensions.join(', ')}`)
      return
    }

    setIsCreatingFile(true)

    try {
      // Create default content based on file type
      let defaultContent = ''
      
      if (extension === 'js' || extension === 'mjs') {
        defaultContent = `// ${filename}

export function example() {
  // Your code here
  return 'Hello from ${filename}';
}
`
      } else if (extension === 'py') {
        defaultContent = `# ${filename}

def example():
    """Your code here"""
    return f"Hello from ${filename}"
`
      } else if (extension === 'json') {
        defaultContent = `{
  "name": "${filename.replace('.json', '')}",
  "version": "1.0.0"
}
`
      } else if (extension === 'md') {
        defaultContent = `# ${filename.replace('.md', '')}

Your documentation here.
`
      } else if (extension === 'html') {
        defaultContent = `<!DOCTYPE html>
<html>
<head>
    <title>${filename.replace('.html', '')}</title>
</head>
<body>
    <h1>Hello from ${filename}</h1>
</body>
</html>
`
      } else if (extension === 'css') {
        defaultContent = `/* ${filename} */

.example {
  /* Your styles here */
}
`
      } else if (extension === 'yml' || extension === 'yaml') {
        defaultContent = `# ${filename}
name: ${filename.replace(/\.(yml|yaml)$/, '')}
version: "1.0.0"
`
      } else if (extension === 'toml') {
        defaultContent = `# ${filename}
[package]
name = "${filename.replace('.toml', '')}"
version = "1.0.0"
`
      } else {
        defaultContent = `# ${filename}

Your content here.
`
      }

      // Create file using the upload API with default content
      const blob = new Blob([defaultContent], { type: 'text/plain' })
      const file = new (window as any).File([blob], filename, { type: 'text/plain' })
      
      await uploadFile(file)
      
      // Refresh the file list to ensure state is synchronized
      await refreshFiles()
      
      // Close dialog and reset form
      setIsNewFileDialogOpen(false)
      setNewFileName("")
      
      // Notify parent that a file was created and select it
      onFileUploaded?.(filename)
      onFileSelect?.(filename)
      
    } catch (error) {
      console.error('Failed to create file:', error)
      toast.error('Failed to create file')
    } finally {
      setIsCreatingFile(false)
    }
  }

  const handleNewFileDialogClose = () => {
    setIsNewFileDialogOpen(false)
    setNewFileName("")
  }

  const getFileIcon = (name: string) => {
    if (name.endsWith('.js') || name.endsWith('.mjs')) return <FileText className="h-4 w-4 text-yellow-500" />
    if (name.endsWith('.ts') || name.endsWith('.tsx')) return <FileText className="h-4 w-4 text-blue-500" />
    if (name.endsWith('.py')) return <FileText className="h-4 w-4 text-green-500" />
    if (name.endsWith('.md')) return <FileText className="h-4 w-4 text-gray-500" />
    if (name.endsWith('.json')) return <FileText className="h-4 w-4 text-yellow-600" />
    if (name.endsWith('.toml') || name.endsWith('.yaml') || name.endsWith('.yml')) return <FileText className="h-4 w-4 text-orange-500" />
    if (name.endsWith('.css') || name.endsWith('.scss')) return <FileText className="h-4 w-4 text-pink-500" />
    if (name.endsWith('.html') || name.endsWith('.htm')) return <FileText className="h-4 w-4 text-orange-600" />
    return <File className="h-4 w-4 text-gray-400" />
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  const filteredFiles = files.filter(file => 
    searchQuery === "" || 
    file.filename.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-3 pb-2 border-b">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium">Explorer</h3>
          <div className="flex items-center gap-1">
            <Button 
              type="button"
              variant="ghost" 
              size="sm" 
              className="h-6 w-6 p-0"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setIsNewFileDialogOpen(true)
              }}
              title="New File"
            >
              <FilePlus className="h-3 w-3" />
            </Button>
            <Button 
              type="button"
              variant="ghost" 
              size="sm" 
              className="h-6 w-6 p-0"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                fileInputRef.current?.click()
              }}
              title="Upload File"
            >
              <Upload className="h-3 w-3" />
            </Button>
            <Button 
              type="button"
              variant="ghost" 
              size="sm" 
              className="h-6 w-6 p-0"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                // Settings action placeholder
              }}
              title="Settings"
            >
              <Settings className="h-3 w-3" />
            </Button>
          </div>
        </div>
        
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={handleFileUpload}
          accept=".js,.mjs,.py,.json,.txt,.md,.html,.css,.yml,.yaml,.toml"
        />
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search files..."
            className="pl-8 h-8 text-xs"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          {/* Project Section */}
          <div className="p-3">
            <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground mb-2">
              <Package className="h-3 w-3" />
              <span>PROJECT FILES ({files.length})</span>
            </div>
            
            {loading ? (
              <div className="text-center py-8 text-muted-foreground">
                <div className="w-6 h-6 border-2 border-muted-foreground border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                <p className="text-xs">Loading files...</p>
              </div>
            ) : filteredFiles.length > 0 ? (
              <div className="space-y-1">
                {filteredFiles.map((file) => (
                  <div
                    key={file.filename}
                    className={`group flex items-center gap-2 px-2 py-1.5 hover:bg-muted/50 cursor-pointer text-sm rounded ${
                      selectedFile === file.filename ? "bg-muted" : ""
                    }`}
                    onClick={() => onFileSelect?.(file.filename)}
                  >
                    {getFileIcon(file.filename)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1">
                        <span className="truncate font-mono text-xs">{file.filename}</span>
                        {file.isDirty && <div className="w-1.5 h-1.5 bg-orange-500 rounded-full flex-shrink-0" />}
                        {file.isLoading && <div className="w-3 h-3 border border-muted-foreground border-t-transparent rounded-full animate-spin flex-shrink-0" />}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatFileSize(file.size)}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteFile(file.filename)
                      }}
                      title="Delete File"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <File className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-xs">No files found</p>
                <p className="text-xs">Upload files to get started</p>
              </div>
            )}
          </div>
          
          <div className="border-t mx-3" />
          
          {/* Quick Actions */}
          <div className="p-3 space-y-2">
            <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground mb-2">
              <Settings className="h-3 w-3" />
              <span>ACTIONS</span>
            </div>
            
            
            <Button 
              type="button"
              variant="ghost" 
              size="sm" 
              className="w-full justify-start h-8 text-xs"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setIsNewFileDialogOpen(true)
              }}
            >
              <FilePlus className="h-3 w-3 mr-2" />
              New File
            </Button>
            
            <Button 
              type="button"
              variant="ghost" 
              size="sm" 
              className="w-full justify-start h-8 text-xs"
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                fileInputRef.current?.click()
              }}
            >
              <Upload className="h-3 w-3 mr-2" />
              Upload File
            </Button>
          </div>
        </ScrollArea>
      </div>
      
      {/* New File Dialog */}
      <Dialog open={isNewFileDialogOpen} onOpenChange={setIsNewFileDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create New File</DialogTitle>
            <DialogDescription>
              Enter a filename with extension. Supported types: js, py, json, md, html, css, yml, txt
            </DialogDescription>
          </DialogHeader>
          
          <form 
            onSubmit={(e) => {
              e.preventDefault()
              if (!isCreatingFile && newFileName.trim()) {
                handleCreateFile()
              }
            }}
          >
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="filename">File Name</Label>
                <Input
                  id="filename"
                  placeholder="example.js"
                  value={newFileName}
                  onChange={(e) => setNewFileName(e.target.value)}
                  disabled={isCreatingFile}
                  autoFocus
                />
              </div>
            </div>
          </form>
          
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={handleNewFileDialogClose}
              disabled={isCreatingFile}
            >
              Cancel
            </Button>
            <Button
              type="button"
              onClick={handleCreateFile}
              disabled={isCreatingFile || !newFileName.trim()}
            >
              {isCreatingFile ? (
                <>
                  <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Creating...
                </>
              ) : (
                <>
                  <FilePlus className="h-4 w-4 mr-2" />
                  Create File
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}