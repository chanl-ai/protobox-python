"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { protoboxClient } from "@/lib/api/protobox-client"
import { toast } from "sonner"

interface CodeFile {
  filename: string
  content: string
  size: number
  lastModified?: string
  isDirty: boolean
  isLoading: boolean
}

interface FileMetadata {
  key: string
  size: number
  last_modified: string
  etag: string
  original_filename: string
  action_id: string
  file_type: string
  content_type: string
}

interface UseActionCodeFilesReturn {
  files: CodeFile[]
  fileMetadata: FileMetadata[]
  loading: boolean
  deploying: boolean
  error: string | null
  loadFiles: () => Promise<void>
  loadFileContent: (filename: string) => Promise<string>
  saveFile: (filename: string, content: string) => Promise<void>
  uploadFile: (file: File) => Promise<void>
  deleteFile: (filename: string) => Promise<void>
  deployAction: () => Promise<void>
  updateFileContent: (filename: string, content: string) => void
  getFile: (filename: string) => CodeFile | undefined
  isFileDirty: (filename: string) => boolean
  hasUnsavedChanges: boolean
  refreshFiles: () => Promise<void>
}

export function useActionCodeFiles(
  workspaceId: string | null,
  actionId: string | null
): UseActionCodeFilesReturn {
  const [files, setFiles] = useState<CodeFile[]>([])
  const [fileMetadata, setFileMetadata] = useState<FileMetadata[]>([])
  const [loading, setLoading] = useState(false)
  const [deploying, setDeploying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Use ref to access current files state in callbacks without causing re-renders
  const filesRef = useRef<CodeFile[]>([])
  // Track loading promises to prevent concurrent requests
  const loadingPromises = useRef<Map<string, Promise<string>>>(new Map())
  // Track which files are currently loading (separate from file state to avoid React batching issues)
  const fileLoadingStates = useRef<Map<string, boolean>>(new Map())
  
  // Update ref whenever files change
  useEffect(() => {
    filesRef.current = files
  }, [files])

  // Load file list (metadata only)
  const loadFiles = useCallback(async () => {
    if (!workspaceId || !actionId) return

    setLoading(true)
    setError(null)

    try {
      const response = await protoboxClient.getActionFiles(workspaceId || undefined, actionId)
      
      if (response.data) {
        setFileMetadata(response.data)
        
        // Initialize files state with metadata but no content
        const fileList: CodeFile[] = response.data.map(meta => ({
          filename: meta.original_filename,
          content: '', // Will be loaded on demand
          size: meta.size,
          lastModified: meta.last_modified,
          isDirty: false,
          isLoading: false,
        }))
        
        setFiles(fileList)
      } else {
        throw new Error(response.error || "Failed to load files")
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load files"
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [workspaceId, actionId])

  // Load content for a specific file
  const loadFileContent = useCallback(async (filename: string): Promise<string> => {
    if (!workspaceId || !actionId) return ''

    // Check if there's already a loading promise for this file
    const existingPromise = loadingPromises.current.get(filename)
    if (existingPromise) {
      return existingPromise
    }

    // Create new loading promise
    const loadingPromise = (async () => {
      try {
        // Set loading state using the separate ref-based system
        fileLoadingStates.current.set(filename, true)

        // First, get the presigned URL
        const response = await protoboxClient.getActionFileContent(workspaceId || undefined, actionId, filename)
        
        if (response.status === 200 && response.data) {
          const { download_url } = response.data
          
          // Now fetch the actual content from the presigned URL
          const contentResponse = await fetch(download_url)
          
          if (!contentResponse.ok) {
            throw new Error(`Failed to fetch file content: ${contentResponse.status} ${contentResponse.statusText}`)
          }
          
          const content = await contentResponse.text()
          
          // Update file content only, loading state managed separately
          setFiles(prev => prev.map(file => 
            file.filename === filename 
              ? { ...file, content }
              : file
          ))
          
          return content
        } else {
          throw new Error(response.error || "Failed to get file download URL")
        }
      } catch (err) {
        console.error('Error loading file content:', filename, err)
        const errorMessage = err instanceof Error ? err.message : "Failed to load file content"
        setError(errorMessage)
        toast.error(errorMessage)
        return ''
      } finally {
        // Always clear loading state and remove from promises when done
        fileLoadingStates.current.set(filename, false)
        loadingPromises.current.delete(filename)
      }
    })()

    // Store the promise
    loadingPromises.current.set(filename, loadingPromise)
    
    return loadingPromise
  }, [workspaceId, actionId])

  // Save a specific file
  const saveFile = useCallback(async (filename: string, content: string) => {
    if (!workspaceId || !actionId) return

    try {
      const response = await protoboxClient.updateActionFileContent(workspaceId || undefined, actionId, filename, content)
      
      if (response.data) {
        // Update file state to reflect saved content
        setFiles(prev => prev.map(file => 
          file.filename === filename 
            ? { ...file, content, isDirty: false, size: content.length }
            : file
        ))
        
        toast.success(`File "${filename}" saved successfully`)
      } else {
        throw new Error(response.error || "Failed to save file")
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to save file"
      setError(errorMessage)
      toast.error(errorMessage)
    }
  }, [workspaceId, actionId])

  // Upload a new file
  const uploadFile = useCallback(async (file: File) => {
    if (!workspaceId || !actionId) return

    try {
      const response = await protoboxClient.uploadActionFile(workspaceId || undefined, actionId, file)
      
      if (response.data) {
        // Reload file list to include new file - call loadFiles directly
        if (workspaceId && actionId) {
          const fileResponse = await protoboxClient.getActionFiles(workspaceId || undefined, actionId)
          if (fileResponse.data) {
            setFileMetadata(fileResponse.data)
            
            // Preserve existing content for files that are already loaded
            const existingFileMap = new Map(filesRef.current.map(f => [f.filename, f]))
            
            const fileList: CodeFile[] = fileResponse.data.map(meta => {
              const existingFile = existingFileMap.get(meta.original_filename)
              return {
                filename: meta.original_filename,
                content: existingFile?.content || '', // Preserve existing content
                size: meta.size,
                lastModified: meta.last_modified,
                isDirty: existingFile?.isDirty || false, // Preserve dirty state
                isLoading: false,
              }
            })
            setFiles(fileList)
          }
        }
        toast.success(`File "${file.name}" uploaded successfully`)
      } else {
        throw new Error(response.error || "Failed to upload file")
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to upload file"
      setError(errorMessage)
      toast.error(errorMessage)
    }
  }, [workspaceId, actionId])

  // Delete a file
  const deleteFile = useCallback(async (filename: string) => {
    if (!workspaceId || !actionId) return

    try {
      const response = await protoboxClient.deleteActionFile(workspaceId || undefined, actionId, filename)
      
      if (response.status === 204 || !response.error) {
        // Remove file from state
        setFiles(prev => prev.filter(file => file.filename !== filename))
        setFileMetadata(prev => prev.filter(meta => meta.original_filename !== filename))
        toast.success(`File "${filename}" deleted successfully`)
      } else {
        throw new Error(response.error || "Failed to delete file")
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to delete file"
      setError(errorMessage)
      toast.error(errorMessage)
    }
  }, [workspaceId, actionId])

  // Deploy action
  const deployAction = useCallback(async () => {
    if (!workspaceId || !actionId) return

    setDeploying(true)
    setError(null)

    try {
      const response = await protoboxClient.deployAction(workspaceId || undefined, actionId)
      
      if (response.data) {
        toast.success(`Action deployed successfully! Deployed ${response.data.user_files} files.`)
      } else {
        throw new Error(response.error || "Failed to deploy action")
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to deploy action"
      setError(errorMessage)
      toast.error(errorMessage)
    } finally {
      setDeploying(false)
    }
  }, [workspaceId, actionId])

  // Update file content in memory (marks as dirty)
  const updateFileContent = useCallback((filename: string, content: string) => {
    setFiles(prev => prev.map(file => 
      file.filename === filename 
        ? { ...file, content, isDirty: true, size: content.length }
        : file
    ))
  }, [])

  // Get a specific file - use ref to avoid re-creating the function
  const getFile = useCallback((filename: string): CodeFile | undefined => {
    const file = filesRef.current.find(f => f.filename === filename)
    if (file) {
      // Use the separate loading state to avoid React batching issues
      const isActuallyLoading = fileLoadingStates.current.get(filename) || false
      return { ...file, isLoading: isActuallyLoading }
    }
    return file
  }, []) // No dependencies needed - uses ref

  // Check if a file is dirty - use ref to avoid re-creating the function
  const isFileDirty = useCallback((filename: string): boolean => {
    const file = filesRef.current.find(f => f.filename === filename)
    return file?.isDirty || false
  }, []) // No dependencies needed - uses ref

  // Check if any files have unsaved changes
  const hasUnsavedChanges = files.some(file => file.isDirty)

  // Refresh files (alias for loadFiles for external use)
  const refreshFiles = useCallback(async () => {
    await loadFiles()
  }, [loadFiles])

  // Load files when workspace or action changes
  useEffect(() => {
    if (workspaceId && actionId) {
    loadFiles()
    }
  }, [workspaceId, actionId]) // Remove loadFiles dependency to avoid infinite loop

  return {
    files,
    fileMetadata,
    loading,
    deploying,
    error,
    loadFiles,
    loadFileContent,
    saveFile,
    uploadFile,
    deleteFile,
    deployAction,
    updateFileContent,
    getFile,
    isFileDirty,
    hasUnsavedChanges,
    refreshFiles,
  }
}
