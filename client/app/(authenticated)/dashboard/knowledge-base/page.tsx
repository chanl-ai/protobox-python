"use client"

import { useState, useRef, useCallback, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { 
  Search, 
  Upload,
  Link,
  Plug,
  Type,
  Database,
  FileText,
  Activity,
  Plus,
  ChevronDown,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
} from "lucide-react"
import { DataTable } from "@/components/knowledge-base/data-table"
import { columns, type DataSource } from "@/components/knowledge-base/columns"
import { protoboxClient } from "@/lib/api/protobox-client"
import { useToast, useWorkspaceReady } from "@/hooks"
import { loggers } from "@/lib/logger"

interface UploadTask {
  id: string
  filename?: string
  url?: string
  title?: string
  sourceType: 'file' | 'url' | 'text'
  status: 'uploading' | 'processing' | 'completed' | 'failed'
  progress?: number
  currentStage?: string
  error?: string
  warnings?: string[]
  entryId?: string
  totalChunks?: number
}

interface ProcessingConfig {
  supportedFileTypes: string[]
  chunkingStrategies: string[]
  maxFileSizeMb: number
  systemStatus: {
    storageAvailable: boolean
    embeddingServiceAvailable: boolean
    parsersCount: number
    chunkersCount: number
  }
  warnings: string[]
  errors: string[]
}

export default function KnowledgeBasePage() {
  const [testQueryOpen, setTestQueryOpen] = useState(false)
  const [addSourceOpen, setAddSourceOpen] = useState(false)
  const [sourceType, setSourceType] = useState<string>("")
  const [uploadTasks, setUploadTasks] = useState<UploadTask[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()
  
  // Enhanced form state
  const [selectedChunkingStrategy, setSelectedChunkingStrategy] = useState<string>("smart")
  const [urlInput, setUrlInput] = useState("")
  const [crawlDepth, setCrawlDepth] = useState(3)
  const [textContent, setTextContent] = useState("")
  const [textTitle, setTextTitle] = useState("")
  const [processingConfig, setProcessingConfig] = useState<ProcessingConfig | null>(null)
  const [configLoading, setConfigLoading] = useState(true)
  
  // Real workspace integration
  const { isReady, workspaceId, user, getDependencies } = useWorkspaceReady()
  
  // Real data state
  const [documents, setDocuments] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Search/query state
  const [query, setQuery] = useState("")
  const [queryResults, setQueryResults] = useState<any[]>([])
  const [queryLoading, setQueryLoading] = useState(false)
  const [queryError, setQueryError] = useState<string | null>(null)
  const [searchType, setSearchType] = useState<string>("hybrid")
  
  const handleSearchTypeChange = useCallback((value: string) => {
    setSearchType(value)
  }, [])
  const [viewDrawerOpen, setViewDrawerOpen] = useState(false)
  const [viewDocument, setViewDocument] = useState<any | null>(null)
  const [viewChunks, setViewChunks] = useState<any[]>([])
  const [reuploadDialogOpen, setReuploadDialogOpen] = useState(false)
  const [reuploadTarget, setReuploadTarget] = useState<any | null>(null)
  const [reuploadFile, setReuploadFile] = useState<File | null>(null)
  const [reuploadText, setReuploadText] = useState<string>("")
  const [reuploadUrl, setReuploadUrl] = useState<string>("")
  const [reuploadType, setReuploadType] = useState<'file'|'text'|'url'>('file')
  
  // Load documents when workspace is ready
  useEffect(() => {
    if (!isReady || !workspaceId) return
    
    loadDocuments()
  }, [isReady, workspaceId])

  // Listen for row action events
  useEffect(() => {
    const onView = (e: any) => handleView(e.detail.source)
    const onEdit = (e: any) => handleEdit(e.detail.source)
    const onRefresh = (e: any) => handleRefresh(e.detail.source)
    const onDelete = (e: any) => handleDelete(e.detail.source)
    if (typeof window !== 'undefined') {
      window.addEventListener('kb:view', onView)
      window.addEventListener('kb:edit', onEdit)
      window.addEventListener('kb:refresh', onRefresh)
      window.addEventListener('kb:delete', onDelete)
    }
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('kb:view', onView)
        window.removeEventListener('kb:edit', onEdit)
        window.removeEventListener('kb:refresh', onRefresh)
        window.removeEventListener('kb:delete', onDelete)
      }
    }
  }, [workspaceId])
  
  const loadDocuments = async () => {
    if (!workspaceId) return

    try {
      setLoading(true)
      setError(null)
      const response = await protoboxClient.listKnowledgeDocuments(workspaceId)

      if (response.error) {
        throw new Error(response.error)
      }

      // Transform backend response to frontend format
      const docs = response.data || []
      const transformedData: DataSource[] = docs.map((doc: any) => ({
        id: doc.id,
        name: doc.title,
        type: doc.source_type === 'url' ? 'webpage' : 'document',
        status: doc.processing_status === 'completed' ? 'indexed' :
               doc.processing_status === 'failed' ? 'failed' : 'processing',
        size: doc.filename ? 'Unknown' : undefined,
        chunks: doc.chunk_count || 0,
        lastUpdated: new Date(doc.updated_at || doc.created_at),
        metadata: {
          fileType: doc.filename ? doc.filename.split('.').pop()?.toLowerCase() : 'url',
          category: doc.category,
          tags: doc.tags
        },
      }))

      setDocuments(transformedData)
    } catch (err) {
      setError('Failed to load knowledge base documents')
      toast({
        title: "Failed to load documents",
        description: err instanceof Error ? err.message : "Could not fetch knowledge base documents. Please try again.",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  // File upload functions
  const handleFileUpload = useCallback(async (files: FileList | File[]) => {
    if (!workspaceId) {
      toast({
        title: "Workspace not ready",
        description: "Please wait for workspace to load before uploading files.",
        variant: "destructive",
      })
      return
    }
    
    const fileArray = Array.from(files)
    
    for (const file of fileArray) {
      // Validate file type
      const supportedTypes = ['.txt', '.md', '.pdf', '.docx', '.xlsx', '.csv']
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase()
      
      if (!supportedTypes.includes(fileExt)) {
        toast({
          title: "Unsupported file type",
          description: `${file.name} is not a supported file type. Supported: ${supportedTypes.join(', ')}`,
          variant: "destructive",
        })
        continue
      }
      
      // Validate file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        toast({
          title: "File too large",
          description: `${file.name} is too large. Maximum size: 10MB`,
          variant: "destructive",
        })
        continue
      }
      
      const taskId = Math.random().toString(36).substr(2, 9)
      const newTask: UploadTask = {
        id: taskId,
        filename: file.name,
        sourceType: 'file',
        status: 'uploading'
      }
      
      setUploadTasks(prev => [...prev, newTask])
      
      try {
        const logger = loggers.ui.child('KB-Page');
        
        logger.debug('Starting file upload', {
          fileName: file.name,
          workspaceId,
          uploadOptions: {
            chunking_strategy: selectedChunkingStrategy,
            category: 'general'
          }
        });
        
        // Upload file
        const response = await protoboxClient.uploadKnowledgeFile(workspaceId, file, {
          chunking_strategy: selectedChunkingStrategy,
          category: 'general'
        })
        
        logger.debug('Upload response received', { response });

        // Check for error response
        if (response.error) {
          throw new Error(response.error)
        }

        // Check if response contains task_id (success)
        if (response.data?.task_id) {
          logger.info('Upload successful, starting polling', {
            taskId: response.data.task_id,
            documentId: response.data.document_id,
            fileName: file.name
          });

          // Success case
          setUploadTasks(prev => prev.map(task =>
            task.id === taskId
              ? { ...task, status: 'processing' }
              : task
          ))

          // Poll for completion
          pollTaskStatus(response.data.task_id, taskId)

          toast({
            title: "File uploaded",
            description: `${file.name} has been uploaded and is being processed.`,
          })
        } else {
          logger.error('Invalid response - no task_id', { response });
          // Response doesn't have task_id - treat as error
          throw new Error('Upload failed - no task ID returned')
        }
        
      } catch (error) {
        const logger = loggers.ui.child('KB-Page');
        logger.error('File upload error', { 
          fileName: file.name,
          errorMessage: error instanceof Error ? error.message : 'Unknown error'
        }, error instanceof Error ? error : undefined);
        
        setUploadTasks(prev => prev.map(task => 
          task.id === taskId 
            ? { ...task, status: 'failed', error: error instanceof Error ? error.message : 'Upload failed' }
            : task
        ))
        
        toast({
          title: "Upload failed",
          description: `Failed to upload ${file.name}: ${error instanceof Error ? error.message : 'Unknown error'}`,
          variant: "destructive",
        })
      }
    }
  }, [workspaceId, selectedChunkingStrategy, toast])
  
  const pollTaskStatus = useCallback(async (serverTaskId: string, localTaskId: string) => {
    if (!workspaceId) return
    
    const maxAttempts = 60 // 5 minutes with 5-second intervals
    let attempts = 0
    
    const poll = async () => {
      try {
        const response = await protoboxClient.getKnowledgeUploadStatus(workspaceId, serverTaskId)

        if (response.error) {
          throw new Error(response.error)
        }

        const status = response.data

        setUploadTasks(prev => prev.map(task =>
          task.id === localTaskId
            ? {
                ...task,
                status: status?.status === 'completed' ? 'completed' :
                       status?.status === 'failed' ? 'failed' : 'processing',
                error: status?.error_message
              }
            : task
        ))

        if (status?.status === 'completed') {
          toast({
            title: "Processing complete",
            description: `${status?.filename || 'Document'} has been successfully processed and added to your knowledge base.`,
          })
          // Refresh the documents list
          loadDocuments()
          return
        }

        if (status?.status === 'failed') {
          toast({
            title: "Processing failed",
            description: `Failed to process ${status?.filename || 'document'}: ${status?.error_message || 'Unknown error'}`,
            variant: "destructive",
          })
          return
        }
        
        // Continue polling
        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000) // Poll every 5 seconds
        } else {
          setUploadTasks(prev => prev.map(task => 
            task.id === localTaskId 
              ? { ...task, status: 'failed', error: 'Processing timeout' }
              : task
          ))
        }
        
      } catch (error) {
        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000)
        }
      }
    }
    
    setTimeout(poll, 2000) // Start polling after 2 seconds
  }, [workspaceId, toast, loadDocuments])
  
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])
  
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])
  
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileUpload(files)
    }
  }, [handleFileUpload])
  
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileUpload(files)
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [handleFileUpload])
  
  const removeUploadTask = useCallback((taskId: string) => {
    setUploadTasks(prev => prev.filter(task => task.id !== taskId))
  }, [])

  // Query/search handler
  const handleQuery = useCallback(async () => {
    if (!workspaceId || !query.trim()) {
      toast({
        title: "Query required",
        description: "Please enter a search query.",
        variant: "destructive",
      })
      return
    }

    try {
      setQueryLoading(true)
      setQueryError(null)

      const response = await protoboxClient.queryKnowledge(workspaceId, query.trim(), {
        top_k: 10,
        search_type: searchType as 'semantic' | 'keyword' | 'hybrid'
      })

      if (response.error) {
        throw new Error(response.error)
      }

      const mapped = (response.data?.results || []).map((r: any) => ({
        document_title: r.document_title,
        score: r.relevance_score,
        content: r.content_snippet,
        metadata: {
          chunk_type: r.chunk_type,
          token_count: r.token_count,
          chunk_index: r.chunk_index,
        }
      }))
      setQueryResults(mapped)
      
      toast({
        title: "Search complete",
        description: `Found ${response.data?.total_results || 0} results in ${response.data?.search_time_ms || 0}ms`,
      })
      
    } catch (error) {
      setQueryError('Search failed')
      toast({
        title: "Search failed",
        description: "Could not search knowledge base. Please try again.",
        variant: "destructive",
      })
    } finally {
      setQueryLoading(false)
    }
  }, [workspaceId, query, searchType, toast])

  // Row action handlers
  const handleView = async (source: any) => {
    if (!workspaceId) return
    try {
      setViewDocument(source)
      setViewChunks([])
      const res = await protoboxClient.getKnowledgeDocument(workspaceId, source.id)
      if (res.error) {
        throw new Error(res.error)
      }
      setViewChunks(res.data?.chunks || [])
      setViewDrawerOpen(true)
    } catch (e) {
      toast({ title: 'Failed to load chunks', variant: 'destructive' })
    }
  }

  const handleEdit = (source: any) => {
    setReuploadTarget(source)
    setReuploadType('file')
    setReuploadFile(null)
    setReuploadUrl("")
    setReuploadText("")
    setReuploadDialogOpen(true)
  }

  const handleRefresh = async (source: any) => {
    await loadDocuments()
    toast({ title: 'Refreshed', description: 'Data source refreshed.' })
  }

  const handleDelete = async (source: any) => {
    if (!workspaceId) return
    try {
      await protoboxClient.deleteKnowledgeDocument(workspaceId, source.id)
      await loadDocuments()
      toast({ title: 'Deleted', description: 'Data source deleted.' })
    } catch (e) {
      toast({ title: 'Delete failed', variant: 'destructive' })
    }
  }

  const submitReupload = async () => {
    if (!workspaceId || !reuploadTarget) return
    try {
      if (reuploadType === 'file') {
        if (!reuploadFile) throw new Error('No file selected')
        await protoboxClient.replaceKnowledgeFile(workspaceId, reuploadTarget.id, reuploadFile, {
          chunking_strategy: selectedChunkingStrategy,
        })
      } else if (reuploadType === 'url') {
        if (!reuploadUrl) throw new Error('No URL provided')
        await protoboxClient.replaceKnowledgeUrl(workspaceId, reuploadTarget.id, reuploadUrl, {
          chunking_strategy: selectedChunkingStrategy,
        })
      } else if (reuploadType === 'text') {
        if (!reuploadText) throw new Error('No text provided')
        await protoboxClient.replaceKnowledgeText(workspaceId, reuploadTarget.id, reuploadText, {
          chunking_strategy: selectedChunkingStrategy,
        })
      }
      setReuploadDialogOpen(false)
      await loadDocuments()
      toast({ title: 'Overwrite started', description: 'Processing has been queued.' })
    } catch (e: any) {
      toast({ title: 'Overwrite failed', description: e?.message || 'Error', variant: 'destructive' })
    }
  }

  // URL upload handler
  const handleUrlUpload = useCallback(async () => {
    if (!workspaceId || !urlInput.trim()) {
      toast({
        title: "URL required",
        description: "Please enter a valid URL.",
        variant: "destructive",
      })
      return
    }

    const taskId = Math.random().toString(36).substr(2, 9)
    const newTask: UploadTask = {
      id: taskId,
      url: urlInput.trim(),
      sourceType: 'url',
      status: 'uploading'
    }
    
    setUploadTasks(prev => [...prev, newTask])

    try {
      const response = await protoboxClient.uploadKnowledgeUrl(workspaceId, urlInput.trim(), {
        chunking_strategy: selectedChunkingStrategy,
        category: 'general'
      })

      if (response.error) {
        throw new Error(response.error)
      }

      if (!response.data?.task_id) {
        throw new Error('Upload failed - no task ID returned')
      }

      setUploadTasks(prev => prev.map(task =>
        task.id === taskId
          ? { ...task, status: 'processing' }
          : task
      ))

      pollTaskStatus(response.data.task_id, taskId)

      toast({
        title: "URL added",
        description: `${urlInput} has been added and is being processed.`,
      })

      // Reset form
      setUrlInput("")
      setAddSourceOpen(false)

    } catch (error) {
      setUploadTasks(prev => prev.map(task => 
        task.id === taskId 
          ? { ...task, status: 'failed', error: error instanceof Error ? error.message : 'Upload failed' }
          : task
      ))
      
      toast({
        title: "URL upload failed",
        description: `Failed to process URL: ${error instanceof Error ? error.message : 'Unknown error'}`,
        variant: "destructive",
      })
    }
  }, [workspaceId, urlInput, selectedChunkingStrategy, toast, pollTaskStatus])

  // Text upload handler
  const handleTextUpload = useCallback(async () => {
    if (!workspaceId || !textTitle.trim() || !textContent.trim()) {
      toast({
        title: "Title and content required",
        description: "Please enter both a title and content.",
        variant: "destructive",
      })
      return
    }

    const taskId = Math.random().toString(36).substr(2, 9)
    const newTask: UploadTask = {
      id: taskId,
      title: textTitle.trim(),
      sourceType: 'text',
      status: 'uploading'
    }
    
    setUploadTasks(prev => [...prev, newTask])

    try {
      const response = await protoboxClient.uploadKnowledgeText(workspaceId, textTitle.trim(), textContent.trim(), {
        chunking_strategy: selectedChunkingStrategy,
        category: 'general'
      })

      if (response.error) {
        throw new Error(response.error)
      }

      if (!response.data?.task_id) {
        throw new Error('Upload failed - no task ID returned')
      }

      setUploadTasks(prev => prev.map(task =>
        task.id === taskId
          ? { ...task, status: 'processing' }
          : task
      ))

      pollTaskStatus(response.data.task_id, taskId)

      toast({
        title: "Text added",
        description: `"${textTitle}" has been added and is being processed.`,
      })

      // Reset form
      setTextTitle("")
      setTextContent("")
      setAddSourceOpen(false)

    } catch (error) {
      setUploadTasks(prev => prev.map(task => 
        task.id === taskId 
          ? { ...task, status: 'failed', error: error instanceof Error ? error.message : 'Upload failed' }
          : task
      ))
      
      toast({
        title: "Text upload failed",
        description: `Failed to process text: ${error instanceof Error ? error.message : 'Unknown error'}`,
        variant: "destructive",
      })
    }
  }, [workspaceId, textTitle, textContent, selectedChunkingStrategy, toast, pollTaskStatus])

  // Reset form when dialog closes
  const handleAddSourceOpenChange = useCallback((open: boolean) => {
    setAddSourceOpen(open)
    if (!open) {
      // Reset form state when closing
      setUrlInput("")
      setTextTitle("")
      setTextContent("")
      setSourceType("")
    }
  }, [])

  // Show loading state while workspace is not ready
  if (!isReady) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  // Mock stats for now - will be replaced with real data later
  const stats = [
    {
      title: "Total Documents",
      value: documents.length.toString(),
      description: "Documents indexed",
      icon: Database,
    },
    {
      title: "Total Chunks",
      value: documents.reduce((acc, doc) => acc + (doc.chunks || 0), 0).toString(),
      description: "Searchable chunks",
      icon: Activity,
    },
    {
      title: "Processing",
      value: documents.filter(doc => doc.status === 'processing').length.toString(),
      description: "Currently processing",
      icon: Loader2,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
          <p className="text-muted-foreground">
            Manage your knowledge sources and test queries
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={() => setTestQueryOpen(true)}
          >
            <Search className="mr-2 h-4 w-4" />
            Test Query
          </Button>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Add Source
                <ChevronDown className="ml-2 h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem
                onClick={() => {
                  setSourceType("document")
                  setAddSourceOpen(true)
                }}
              >
                <Upload className="mr-2 h-4 w-4" />
                Upload Document
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => {
                  setSourceType("url")
                  setAddSourceOpen(true)
                }}
              >
                <Link className="mr-2 h-4 w-4" />
                Add URL
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => {
                  setSourceType("integration")
                  setAddSourceOpen(true)
                }}
              >
                <Plug className="mr-2 h-4 w-4" />
                Connect Integration
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={() => {
                  setSourceType("text")
                  setAddSourceOpen(true)
                }}
              >
                <Type className="mr-2 h-4 w-4" />
                Add Text
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {stats.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Data Sources Content */}
      <Card>
        <CardHeader>
          <CardTitle>Data Sources</CardTitle>
          <CardDescription>
            Manage your knowledge base sources with advanced filtering and search
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} data={documents} />
        </CardContent>
      </Card>

      {/* Test Query Dialog */}
      <Dialog open={testQueryOpen} onOpenChange={setTestQueryOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Test Knowledge Base Query</DialogTitle>
            <DialogDescription>
              Test how your knowledge base responds to questions
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="query">Your Question</Label>
              <Textarea
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask a question about your documents..."
                className="min-h-[100px]"
              />
            </div>
            <div className="space-y-2">
              <Label>Search Type</Label>
              <Select value={searchType} onValueChange={handleSearchTypeChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select search type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="hybrid">Hybrid</SelectItem>
                  <SelectItem value="semantic">Semantic</SelectItem>
                  <SelectItem value="keyword">Keyword</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="source">Source Filter (Optional)</Label>
              <Select>
                <SelectTrigger>
                  <SelectValue placeholder="All sources" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All sources</SelectItem>
                  <SelectItem value="documents">Documents only</SelectItem>
                  <SelectItem value="web">Web pages only</SelectItem>
                  <SelectItem value="integrations">Integrations only</SelectItem>
                  <SelectItem value="text">Text snippets only</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Results</Label>
              <Card>
                <CardContent className="pt-4 max-h-80 overflow-y-auto">
                  {queryLoading && (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="h-6 w-6 animate-spin" />
                      <span className="ml-2 text-sm text-muted-foreground">Searching...</span>
                    </div>
                  )}
                  
                  {queryError && (
                    <div className="flex items-center py-4">
                      <AlertCircle className="h-4 w-4 text-red-500 mr-2" />
                      <span className="text-sm text-red-500">{queryError}</span>
                    </div>
                  )}
                  
                  {!queryLoading && !queryError && queryResults.length === 0 && query && (
                    <p className="text-sm text-muted-foreground py-4">
                      No results found for "{query}". Try different search terms.
                    </p>
                  )}
                  
                  {!queryLoading && !queryError && queryResults.length === 0 && !query && (
                    <p className="text-sm text-muted-foreground py-4">
                      Query results will appear here...
                    </p>
                  )}
                  
                  {!queryLoading && queryResults.length > 0 && (
                    <div className="space-y-4">
                      {queryResults.map((result, index) => (
                        <div key={index} className="border-b border-border pb-4 last:border-b-0">
                          <div className="flex items-start justify-between mb-2">
                            <h4 className="text-sm font-medium truncate flex-1">
                              {result.document_title || 'Unknown Document'}
                            </h4>
                            <span className="text-xs text-muted-foreground ml-2">
                              Score: {(result.score * 100).toFixed(1)}%
                            </span>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2 line-clamp-3">
                            {result.content || 'No content preview available'}
                          </p>
                          {result.metadata && result.metadata.chunk_type && (
                            <span className="text-xs px-2 py-1 bg-muted rounded text-muted-foreground">
                              {result.metadata.chunk_type}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setTestQueryOpen(false)
              setQuery("")
              setQueryResults([])
              setQueryError(null)
              setSearchType("hybrid")
            }}>
              Close
            </Button>
            <Button onClick={handleQuery} disabled={queryLoading}>
              {queryLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              {queryLoading ? "Searching..." : "Search"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Source Dialog */}
      <Dialog open={addSourceOpen} onOpenChange={handleAddSourceOpenChange}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {sourceType === "document" && "Upload Document"}
              {sourceType === "url" && "Add URL"}
              {sourceType === "integration" && "Connect Integration"}
              {sourceType === "text" && "Add Text"}
            </DialogTitle>
            <DialogDescription>
              Add a new data source to your knowledge base
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Chunking strategy selection */}
            <div className="space-y-2">
              <Label>Chunking Strategy</Label>
              <Select value={selectedChunkingStrategy} onValueChange={setSelectedChunkingStrategy}>
                <SelectTrigger>
                  <SelectValue placeholder="Select strategy" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="smart">Smart</SelectItem>
                  <SelectItem value="faq_optimization">FAQ Optimization</SelectItem>
                  <SelectItem value="topic_headers">Topic Headers</SelectItem>
                  <SelectItem value="summarize">Summarize</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {sourceType === "document" && (
              <div className="space-y-4">
                <div 
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    isDragOver ? 'border-primary bg-primary/10' : 'border-muted-foreground/25'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">
                    Drag and drop files here, or click to browse
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Supports PDF, DOCX, TXT, MD, XLSX, CSV (max 10MB)
                  </p>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="mt-4"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Browse Files
                  </Button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".txt,.md,.pdf,.docx,.xlsx,.csv"
                    onChange={handleFileInputChange}
                    className="hidden"
                  />
                </div>
                
                {/* Upload Progress */}
                {uploadTasks.length > 0 && (
                  <div className="space-y-2">
                    <Label>Upload Progress</Label>
                    <div className="max-h-32 overflow-y-auto space-y-2">
                      {uploadTasks.map((task) => (
                        <div key={task.id} className="flex items-center justify-between p-2 border rounded">
                          <div className="flex items-center space-x-2 flex-1">
                            {task.status === 'uploading' && <Loader2 className="h-4 w-4 animate-spin" />}
                            {task.status === 'processing' && <Loader2 className="h-4 w-4 animate-spin" />}
                            {task.status === 'completed' && <CheckCircle className="h-4 w-4 text-green-500" />}
                            {task.status === 'failed' && <AlertCircle className="h-4 w-4 text-red-500" />}
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{task.filename}</p>
                              <p className="text-xs text-muted-foreground">
                                {task.status === 'uploading' && 'Uploading...'}
                                {task.status === 'processing' && 'Processing...'}
                                {task.status === 'completed' && 'Completed'}
                                {task.status === 'failed' && (task.error || 'Failed')}
                              </p>
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeUploadTask(task.id)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            {sourceType === "url" && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="url">URL</Label>
                  <Input 
                    id="url" 
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    placeholder="https://example.com" 
                  />
                </div>
              </div>
            )}
            {sourceType === "integration" && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Card className="cursor-pointer hover:border-primary">
                    <CardContent className="p-4 text-center">
                      <Plug className="mx-auto h-8 w-8 mb-2" />
                      <p className="font-medium">Zendesk</p>
                    </CardContent>
                  </Card>
                  <Card className="cursor-pointer hover:border-primary">
                    <CardContent className="p-4 text-center">
                      <Plug className="mx-auto h-8 w-8 mb-2" />
                      <p className="font-medium">Intercom</p>
                    </CardContent>
                  </Card>
                  <Card className="cursor-pointer hover:border-primary">
                    <CardContent className="p-4 text-center">
                      <Plug className="mx-auto h-8 w-8 mb-2" />
                      <p className="font-medium">HubSpot</p>
                    </CardContent>
                  </Card>
                  <Card className="cursor-pointer hover:border-primary">
                    <CardContent className="p-4 text-center">
                      <Plug className="mx-auto h-8 w-8 mb-2" />
                      <p className="font-medium">Slack</p>
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}
            {sourceType === "text" && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Title</Label>
                  <Input 
                    id="title" 
                    value={textTitle}
                    onChange={(e) => setTextTitle(e.target.value)}
                    placeholder="e.g., Company FAQ" 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="content">Content</Label>
                  <Textarea
                    id="content"
                    value={textContent}
                    onChange={(e) => setTextContent(e.target.value)}
                    placeholder="Enter or paste your text content..."
                    className="min-h-[200px]"
                  />
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => handleAddSourceOpenChange(false)}>
              Cancel
            </Button>
            {sourceType === "url" && (
              <Button onClick={handleUrlUpload}>
                Add URL
              </Button>
            )}
            {sourceType === "text" && (
              <Button onClick={handleTextUpload}>
                Add Text
              </Button>
            )}
            {sourceType === "integration" && (
              <Button disabled>
                Connect (Coming Soon)
              </Button>
            )}
            {sourceType === "document" && uploadTasks.length === 0 && (
              <Button onClick={() => fileInputRef.current?.click()}>
                Browse Files
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View Drawer - right side */}
      {viewDrawerOpen && (
        <div className="fixed top-0 right-0 h-full w-full max-w-[480px] bg-background border-l z-40 shadow-lg flex flex-col">
          <div className="p-4 border-b flex items-center justify-between">
            <div>
              <h3 className="font-semibold">{viewDocument?.name || 'Document'}</h3>
              <p className="text-xs text-muted-foreground">{viewChunks.length} chunks</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setViewDrawerOpen(false)}>
              Close
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {viewChunks.map((c: any) => (
              <div key={c.id} className="p-3 border rounded">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-muted-foreground">#{c.chunk_index} • {c.chunk_type} • {c.token_count} tokens</span>
                  {c.source_metadata?.page_number && (
                    <span className="text-xs">Page {c.source_metadata.page_number}</span>
                  )}
                </div>
                <p className="text-sm whitespace-pre-wrap">{c.content}</p>
              </div>
            ))}
            {viewChunks.length === 0 && (
              <p className="text-sm text-muted-foreground">No chunks to display.</p>
            )}
          </div>
        </div>
      )}

      {/* Overwrite Dialog */}
      <Dialog open={reuploadDialogOpen} onOpenChange={setReuploadDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Overwrite</DialogTitle>
            <DialogDescription>Replace the existing source content for this document.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Source Type</Label>
              <Select value={reuploadType} onValueChange={(v: any) => setReuploadType(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="file">File</SelectItem>
                  <SelectItem value="url">URL</SelectItem>
                  <SelectItem value="text">Text</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Chunking Strategy</Label>
              <Select value={selectedChunkingStrategy} onValueChange={setSelectedChunkingStrategy}>
                <SelectTrigger>
                  <SelectValue placeholder="Select strategy" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="smart">Smart</SelectItem>
                  <SelectItem value="faq_optimization">FAQ Optimization</SelectItem>
                  <SelectItem value="topic_headers">Topic Headers</SelectItem>
                  <SelectItem value="summarize">Summarize</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {reuploadType === 'file' && (
              <div className="space-y-2">
                <Label>Select File</Label>
                <Input 
                  type="file" 
                  accept=".txt,.md,.pdf,.docx,.xlsx,.csv"
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    setReuploadFile(file);
                  }} 
                />
              </div>
            )}
            {reuploadType === 'url' && (
              <div className="space-y-2">
                <Label>URL</Label>
                <Input value={reuploadUrl} onChange={(e) => setReuploadUrl(e.target.value)} placeholder="https://example.com" />
              </div>
            )}
            {reuploadType === 'text' && (
              <div className="space-y-2">
                <Label>Text Content</Label>
                <Textarea value={reuploadText} onChange={(e) => setReuploadText(e.target.value)} placeholder="Enter replacement text..." />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReuploadDialogOpen(false)}>Cancel</Button>
            <Button onClick={submitReupload}>Submit</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}