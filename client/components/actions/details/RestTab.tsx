"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Save, AlertCircle } from "lucide-react"
import { toast } from "sonner"
import { useAuth } from "@/lib/auth"
import { useWorkspaceReady } from "@/hooks"
import { useUpdateAction } from "@/lib/api/hooks"
import { useActionForm } from "./FormProvider"
import { EndpointCard } from "./RestTab/EndpointCard"
import { RequestBodyCard } from "./RestTab/RequestBodyCard"
import { ResponseCard } from "./RestTab/ResponseCard"

export function RestTab() {
  const { form, action } = useActionForm()
  const { isReady, workspaceId } = useWorkspaceReady()
  const params = useParams()
  const actionId = params.actionId as string
  const updateAction = useUpdateAction()
  const [isSaving, setIsSaving] = useState(false)

  // Track if form has unsaved changes for REST-specific fields
  const isDirty = form.formState.isDirty
  const isValid = form.formState.isValid
  const hasErrors = Object.keys(form.formState.errors).length > 0
  
  // Button should be enabled if there are changes and we're not saving
  const canSave = isDirty && !isSaving

  const handleSave = async () => {
    if (!user?.customToken || !isReady || !workspaceId || !actionId) {
      toast.error("Missing required authentication or workspace information")
      return
    }

    try {
      setIsSaving(true)
      
      // Trigger validation
      const isFormValid = await form.trigger()
      if (!isFormValid) {
        toast.error("Please fix validation errors before saving")
        return
      }

      // Get form data
      const formData = form.getValues()
      
      // Map form data to backend API structure - focus on REST-specific fields
      const updateData = {
        // Keep existing basic info
        name: action.name,
        description: action.description,
        version: action.version,
        tags: action.tags,
        config_schema: action.config_schema,
        secret_refs: action.secret_refs,
        
        // Update REST-specific configuration in default_config
        default_config: {
          ...action.default_config,
          method: formData.method,
          url: formData.url,
          headers: formData.headers.reduce((acc: Record<string, string>, header: any) => {
            if (header.key && header.value) {
              acc[header.key] = header.value
            }
            return acc
          }, {}),
          body: formData.body,
          bodyType: formData.bodyType,
          responseTransformation: formData.responseTransformation,
          requestTransformation: formData.requestTransformation
        }
      }

      // Call the update API
      const updatedAction = await updateAction.mutateAsync({
        actionId,
        data: updateData,
      })
      
      if (updatedAction) {
        // Extract relevant fields from the updated action for form reset
        const defaultConfig = updatedAction.default_config || {}
        
        // Convert headers object back to array format for the form
        const headersArray = Object.entries(defaultConfig.headers || {}).map(([key, value]) => ({
          key,
          value: value as string
        }))
        
        const updatedFormData = {
          // Basic info fields (preserve current form values as they're not being saved here)
          name: formData.name,
          description: formData.description,
          type: formData.type,
          version: formData.version,
          tags: formData.tags,
          inputVariables: formData.inputVariables,
          secretRefs: formData.secretRefs,
          
          // REST-specific fields (updated from API response)
          method: defaultConfig.method || "POST",
          url: defaultConfig.url || "",
          headers: headersArray,
          bodyType: defaultConfig.bodyType || "json",
          body: defaultConfig.body || "",
          responseTransformation: defaultConfig.responseTransformation || "{{response}}",
          requestTransformation: defaultConfig.requestTransformation || "",
          
          // CODE_RUN specific fields (preserve current values)
          codeLanguage: formData.codeLanguage,
          sourceCode: formData.sourceCode,
          executionTimeout: formData.executionTimeout,
          environmentVariables: formData.environmentVariables,
          dependencies: formData.dependencies
        }
        
        // Reset form with updated data to clear dirty state
        form.reset(updatedFormData)
        toast.success("REST configuration saved successfully")
      } else {
        throw new Error("Failed to save REST configuration")
      }
    } catch (error) {
      console.error("Save error:", error)
      toast.error("Failed to save REST configuration. Please try again.")
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Save Section */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle className="text-lg">REST Configuration</CardTitle>
              <CardDescription>
                Configure HTTP method, URL, headers, and request/response handling
              </CardDescription>
            </div>
            <div className="flex items-center gap-3">
              {isDirty && (
                <div className="flex items-center gap-2 text-sm text-amber-600">
                  <AlertCircle className="w-4 h-4" />
                  <span>Unsaved changes</span>
                </div>
              )}
              <Button 
                type="button"
                onClick={handleSave}
                disabled={!canSave}
                className="gap-2"
                variant={hasErrors ? "destructive" : "default"}
                title={
                  !isDirty ? "No changes to save" :
                  hasErrors ? "Validation errors will be checked on save" :
                  "Save your REST configuration"
                }
              >
                <Save className="w-4 h-4" />
                {isSaving ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* REST Configuration Cards */}
      <EndpointCard />
      <RequestBodyCard />
      <ResponseCard />
    </div>
  )
}