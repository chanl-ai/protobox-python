"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  Download,
  Loader2,
  ChevronLeft,
  Eye,
} from "lucide-react"
import { toast } from "sonner"
import { ActionsImportAPI, type ImportPreviewResponse, type ImportResult, type ActionPreview } from "../lib/api/actions-import"
import { useAuth } from "@/lib/firebase/auth-context"
import { useWorkspaceReady } from "@/hooks"

// Import child components
import { SourceSelection, type ImportType } from "./import-actions/source-selection"
import { ConfigureStep } from "./import-actions/configure-step"
import { ActionsPreview } from "./import-actions/actions-preview"
import { ImportResults } from "./import-actions/import-results"
import { ProgressIndicator, type ImportStep } from "./import-actions/progress-indicator"

interface ImportActionsDialogProps {
  trigger?: React.ReactNode
  onImportComplete?: (result: ImportResult) => void
}

export function ImportActionsDialog({ trigger, onImportComplete }: ImportActionsDialogProps) {
  const { isReady, workspaceId, user } = useWorkspaceReady()
  const { customToken } = useAuth()
  
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState<ImportStep>("source")
  const [importType, setImportType] = useState<ImportType | "">("openapi")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>("")
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false)

  // OpenAPI form state
  const [openApiForm, setOpenApiForm] = useState({
    specUrl: "",
    specContent: "",
    baseUrlOverride: "",
    includePaths: "",
    excludePaths: "",
    namePrefix: "",
    tags: "imported,openapi",
  })

  // cURL form state
  const [curlForm, setCurlForm] = useState({
    curlCommand: "",
    name: "",
    description: "",
    tags: "imported,curl",
  })

  // Preview state
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null)
  const [selectedActions, setSelectedActions] = useState<Set<string>>(new Set())
  const [importResult, setImportResult] = useState<ImportResult | null>(null)

  const resetForm = () => {
    setStep("source")
    setImportType("openapi")
    setLoading(false)
    setError("")
    setShowAdvancedOptions(false)
    setPreview(null)
    setSelectedActions(new Set())
    setImportResult(null)
    setOpenApiForm({
      specUrl: "",
      specContent: "",
      baseUrlOverride: "",
      includePaths: "",
      excludePaths: "",
      namePrefix: "",
      tags: "imported,openapi",
    })
    setCurlForm({
      curlCommand: "",
      name: "",
      description: "",
      tags: "imported,curl",
    })
  }

  const handleOpenApiPreview = async () => {
    if (!openApiForm.specUrl && !openApiForm.specContent) {
      toast.error("Please provide either a URL or paste the OpenAPI spec")
      return
    }

    if (!isReady || !workspaceId || !user) {
      toast.error("Please wait for workspace to load")
      return
    }

    if (!customToken) {
      toast.error("Authentication required. Please sign in.")
      return
    }

    setLoading(true)
    setError("")

    try {
      
      const request = {
        spec_url: openApiForm.specUrl || undefined,
        spec_content: openApiForm.specContent || undefined,
        base_url_override: openApiForm.baseUrlOverride || undefined,
        include_paths: openApiForm.includePaths ? openApiForm.includePaths.split(',').map((p: string) => p.trim()).filter(Boolean) : undefined,
        exclude_paths: openApiForm.excludePaths ? openApiForm.excludePaths.split(',').map((p: string) => p.trim()).filter(Boolean) : undefined,
      }

      const previewResponse = await ActionsImportAPI.previewOpenAPI(workspaceId, request)
      setPreview(previewResponse)
      setSelectedActions(new Set(previewResponse.previews.map((p: ActionPreview) => p.name)))
      setStep("preview")
      toast.success(`Found ${previewResponse.actions_count} action${previewResponse.actions_count !== 1 ? 's' : ''} to import`)
    } catch (err: any) {
      if (err.response?.status === 404) {
        toast.error("Import feature is not enabled. Please contact your administrator.")
      } else {
        toast.error(err.response?.data?.detail || "Failed to parse OpenAPI spec. Please check the URL or content.")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCurlPreview = async () => {
    if (!curlForm.curlCommand) {
      toast.error("Please provide a cURL command")
      return
    }

    if (!isReady || !workspaceId || !user) {
      toast.error("Please wait for workspace to load")
      return
    }

    if (!customToken) {
      toast.error("Authentication required. Please sign in.")
      return
    }

    setLoading(true)
    setError("")

    try {
      
      const request = {
        curl_command: curlForm.curlCommand,
        name: curlForm.name || undefined,
        description: curlForm.description || undefined,
      }

      const previewResponse = await ActionsImportAPI.previewCurl(workspaceId, request)
      setPreview(previewResponse)
      setSelectedActions(new Set(previewResponse.previews.map((p: ActionPreview) => p.name)))
      setStep("preview")
      toast.success(`Found ${previewResponse.actions_count} action${previewResponse.actions_count !== 1 ? 's' : ''} to import`)
    } catch (err: any) {
      if (err.response?.status === 404) {
        toast.error("Import feature is not enabled. Please contact your administrator.")
      } else {
        toast.error(err.response?.data?.detail || "Failed to parse cURL command. Please check the syntax.")
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCreateActions = async () => {
    if (selectedActions.size === 0) {
      toast.error("Please select at least one action to create")
      return
    }

    if (!isReady || !workspaceId || !user) {
      toast.error("Please wait for workspace to load")
      return
    }

    if (!customToken) {
      toast.error("Authentication required. Please sign in.")
      return
    }

    setLoading(true)
    setError("")

    try {
      
      let result: ImportResult
      
      if (importType === "openapi") {
        const request = {
          spec_url: openApiForm.specUrl || undefined,
          spec_content: openApiForm.specContent || undefined,
          base_url_override: openApiForm.baseUrlOverride || undefined,
          include_paths: openApiForm.includePaths ? openApiForm.includePaths.split(',').map(p => p.trim()).filter(Boolean) : undefined,
          exclude_paths: openApiForm.excludePaths ? openApiForm.excludePaths.split(',').map(p => p.trim()).filter(Boolean) : undefined,
        }
        result = await ActionsImportAPI.createFromOpenAPI(workspaceId, request)
      } else {
        const request = {
          curl_command: curlForm.curlCommand,
          name: curlForm.name || undefined,
          description: curlForm.description || undefined,
        }
        result = await ActionsImportAPI.createFromCurl(workspaceId, request)
      }
      
      setImportResult(result)
      setStep("result")
      onImportComplete?.(result)
      toast.success(`Successfully imported ${result.summary.created} action${result.summary.created !== 1 ? 's' : ''}`)
    } catch (err: any) {
      if (err.response?.status === 404) {
        toast.error("Import feature is not enabled. Please contact your administrator.")
      } else {
        toast.error(err.response?.data?.detail || "Failed to create actions. Please try again.")
      }
    } finally {
      setLoading(false)
    }
  }

  const toggleActionSelection = (actionName: string) => {
    const newSelected = new Set(selectedActions)
    if (newSelected.has(actionName)) {
      newSelected.delete(actionName)
    } else {
      newSelected.add(actionName)
    }
    setSelectedActions(newSelected)
  }

  const selectAllActions = () => {
    if (preview) {
      setSelectedActions(new Set(preview.previews.map((p: ActionPreview) => p.name)))
    }
  }

  const deselectAllActions = () => {
    setSelectedActions(new Set())
  }



  return (
    <Dialog open={open} onOpenChange={(newOpen) => {
      setOpen(newOpen)
      if (!newOpen) {
        resetForm()
      }
    }}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" className="gap-2">
            <Download className="w-4 h-4" />
            Import Actions
          </Button>
        )}
      </DialogTrigger>
      
      <DialogContent className="sm:max-w-[900px] max-h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center justify-between pr-8">
            <div className="flex items-center gap-2">
              <Download className="w-5 h-5" />
              Import Actions
              {step === "preview" && preview && (
                <Badge variant="secondary" className="ml-2">
                  {preview.actions_count} action{preview.actions_count !== 1 ? 's' : ''} found
                </Badge>
              )}
            </div>
            <ProgressIndicator currentStep={step} />
          </DialogTitle>
        </DialogHeader>

        <Separator className="flex-shrink-0" />

        <div className="flex-1 overflow-y-auto min-h-0">
          {/* Step 1: Source */}
          {step === "source" && (
            <SourceSelection
              importType={importType}
              setImportType={setImportType}
            />
          )}

          {/* Step 2: Configure */}
          {step === "configure" && (
            <ConfigureStep
              importType={importType}
              openApiForm={openApiForm}
              setOpenApiForm={setOpenApiForm}
              curlForm={curlForm}
              setCurlForm={setCurlForm}
              showAdvancedOptions={showAdvancedOptions}
              setShowAdvancedOptions={setShowAdvancedOptions}
            />
          )}

          {/* Step 3: Preview */}
          {step === "preview" && preview && (
            <ActionsPreview
              preview={preview}
              selectedActions={selectedActions}
              onToggleAction={toggleActionSelection}
              onSelectAll={selectAllActions}
              onDeselectAll={deselectAllActions}
            />
          )}

          {/* Step 4: Result */}
          {step === "result" && importResult && (
            <ImportResults importResult={importResult} />
          )}
        </div>

        <DialogFooter className="flex justify-between flex-shrink-0">
          <div className="flex gap-2">
            {step !== "source" && (
              <Button
                variant="outline"
                onClick={() => {
                  if (step === "configure") {
                    setStep("source")
                    setError("")
                  } else if (step === "preview") {
                    setStep("configure")
                    setPreview(null)
                    setSelectedActions(new Set())
                    setError("")
                  } else if (step === "result") {
                    setStep("preview")
                    setImportResult(null)
                    setError("")
                  }
                }}
                disabled={loading}
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Back
              </Button>
            )}
          </div>
          
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={loading}
            >
              {step === "result" ? "Close" : "Cancel"}
            </Button>
            
            {step === "source" && (
              <Button
                onClick={() => setStep("configure")}
                disabled={!importType}
              >
                Next
              </Button>
            )}
            
            {step === "configure" && (
              <Button
                onClick={() => {
                  if (importType === "openapi") {
                    handleOpenApiPreview()
                  } else {
                    handleCurlPreview()
                  }
                }}
                disabled={loading || (
                  importType === "openapi" 
                    ? !openApiForm.specUrl && !openApiForm.specContent
                    : !curlForm.curlCommand
                )}
              >
                {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                <Eye className="w-4 h-4 mr-2" />
                Preview Actions
              </Button>
            )}
            
            {step === "preview" && (
              <Button
                onClick={handleCreateActions}
                disabled={loading || selectedActions.size === 0}
              >
                {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Import {selectedActions.size} Action{selectedActions.size !== 1 ? 's' : ''}
              </Button>
            )}
            
            {step === "result" && (
              <Button
                onClick={() => {
                  setOpen(false)
                  if (onImportComplete && importResult) {
                    onImportComplete(importResult)
                  }
                }}
              >
                Done
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
