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
import { BasicInfoCard } from "./GeneralTab/BasicInfoCard"
import { TagsCard } from "./GeneralTab/TagsCard"
import { InputVariablesCard } from "./GeneralTab/InputVariablesCard"
import { SecretsCard } from "./GeneralTab/SecretsCard"

export function GeneralTab() {
  const { form, action } = useActionForm()
  const { isReady, workspaceId } = useWorkspaceReady()
  const params = useParams()
  const actionId = params.actionId as string
  const updateAction = useUpdateAction()
  const [isSaving, setIsSaving] = useState(false)

  // Track if form has unsaved changes
  const isDirty = form.formState.isDirty
  const isValid = form.formState.isValid
  const hasErrors = Object.keys(form.formState.errors).length > 0
  
  // Button should be enabled if there are changes and either valid OR we'll validate on save attempt
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
      
      // Map form data to backend API structure
      const updateData = {
        name: formData.name,
        description: formData.description,
        version: formData.version,
        tags: formData.tags,
        // Map inputVariables to config_schema
        config_schema: {
          inputVariables: formData.inputVariables
        },
        // Keep existing default_config but update if needed
        default_config: action.default_config || {},
        // Map secretRefs to secret_refs
        secret_refs: formData.secretRefs
      }

      // Call the update API
      const updatedAction = await updateAction.mutateAsync({
        actionId,
        data: updateData,
      })
      
      if (updatedAction) {
        const updatedFormData = {
          // Basic info fields
          name: updatedAction.name,
          description: updatedAction.description || "",
          type: updatedAction.type as any,
          version: updatedAction.version || "1.0.0",
          tags: updatedAction.tags || [],
          
          // Input variables from config_schema
          inputVariables: (updatedAction.config_schema as any)?.inputVariables || [],
          
          // Secret references
          secretRefs: updatedAction.secret_refs || [],
          
          // REST API specific fields (preserve current values as they're not saved in general tab)
          method: formData.method,
          url: formData.url,
          headers: formData.headers,
          bodyType: formData.bodyType,
          body: formData.body,
          responseTransformation: formData.responseTransformation,
          requestTransformation: formData.requestTransformation,
          
          // CODE_RUN specific fields (preserve current values)
          codeLanguage: formData.codeLanguage,
          sourceCode: formData.sourceCode,
          executionTimeout: formData.executionTimeout,
          environmentVariables: formData.environmentVariables,
          dependencies: formData.dependencies
        }
        
        // Reset form with updated data to clear dirty state
        form.reset(updatedFormData)
        toast.success("Action saved successfully")
      } else {
        throw new Error("Failed to save action")
      }
    } catch (error) {
      console.error("Save error:", error)
      toast.error("Failed to save action. Please try again.")
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
              <CardTitle className="text-lg">General Settings</CardTitle>
              <CardDescription>
                Configure the basic properties and behavior of your action
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
                  "Save your changes"
                }
              >
                <Save className="w-4 h-4" />
                {isSaving ? "Saving..." : "Save Changes"}
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Form Cards */}
      <BasicInfoCard />
      <TagsCard />
      <InputVariablesCard />
      <SecretsCard />
    </div>
  )
}