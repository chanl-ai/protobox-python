"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { useWorkspaceReady } from "@/hooks"
import { useAction, useUpdateAction, useSecrets, type Action, type Secret } from "@/lib/api/hooks"
import { protoboxClient } from "@/lib/api/protobox-client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TagsInput } from "@/components/ui/tags-input"
import { Separator } from "@/components/ui/separator"
import { Checkbox } from "@/components/ui/checkbox"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { LiquidEditor } from "@/components/liquid-editor"
import { toast } from "sonner"
import { useForm, useFieldArray } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { 
  Save, 
  Play, 
  Plus, 
  X, 
  Globe, 
  Database, 
  Code, 
  BookOpen,
  Settings,
  Zap,
  Loader2,
  ExternalLink,
  Trash2
} from "lucide-react"

// Form validation schemas
const headerSchema = z.object({
  key: z.string().min(1, "Header name is required"),
  value: z.string().min(1, "Header value is required"),
})

const inputVariableSchema = z.object({
  name: z.string().min(1, "Variable name is required"),
  description: z.string().min(1, "Variable description is required"),
  type: z.enum(["string", "number", "boolean"]).default("string"),
  required: z.boolean().default(true),
  default_value: z.string().optional()
})

const actionFormSchema = z.object({
  name: z.string()
    .min(1, "Action name is required")
    .max(255, "Name must be 255 characters or less")
    .regex(/^[a-zA-Z0-9\s\-_]+$/, "Name can only contain letters, numbers, spaces, hyphens, and underscores"),
  description: z.string()
    .min(10, "Description must be at least 10 characters")
    .max(1000, "Description must be 1000 characters or less"),
  type: z.enum(["REST", "DATABASE", "CODE_RUN", "KNOWLEDGE_BASE"]),
  tags: z.array(z.string()).default([]),
  version: z.string()
    .regex(/^\d+\.\d+\.\d+$/, "Version must follow semantic versioning (e.g., 1.0.0)"),
  
  // Input variables for LLM interaction
  inputVariables: z.array(inputVariableSchema).default([]),
  
  // REST API specific
  method: z.enum(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]).default("POST"),
  url: z.string()
    .min(1, "URL is required for REST actions")
    .refine((url) => {
      // Allow URLs with variables like {{variable}}
      const urlWithoutVariables = url.replace(/\{\{[^}]+\}\}/g, 'placeholder')
      try {
        new URL(urlWithoutVariables)
        return true
      } catch {
        return false
      }
    }, "Must be a valid URL (variables like {{city}} are allowed)")
    .refine((url) => {
      // Check for proper variable syntax - must have matching braces
      const braceMatches = url.match(/\{|\}/g)
      if (braceMatches) {
        let openCount = 0
        for (const brace of braceMatches) {
          if (brace === '{') openCount++
          else openCount--
          if (openCount < 0) return false // More closing than opening
        }
        return openCount === 0 // All braces properly matched
      }
      return true
    }, "Variables must use proper {{variable}} syntax with matching braces")
    .optional().or(z.literal("")),
  headers: z.array(headerSchema).default([]),
  bodyType: z.enum(["none", "json", "form", "text"]).default("json"),
  body: z.string().default(""),
  responseTransformation: z.string()
    .min(1, "Response transformation is required")
    .default("{{response}}"),
  requestTransformation: z.string().optional().default(""),
  
  // Common
  secretRefs: z.array(z.string()).default([])
})

type ActionFormData = z.infer<typeof actionFormSchema>

const httpMethods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
const bodyTypes = [
  { value: "none", label: "None" },
  { value: "json", label: "JSON" },
  { value: "form", label: "Form Data" },
  { value: "text", label: "Raw Text" }
]

// Common tag suggestions for actions
const commonTags = [
  "api", "external", "weather", "data", "search", "ai", "ml", "database", 
  "auth", "payment", "email", "notification", "analytics", "monitoring",
  "integration", "webhook", "social", "media", "content", "security",
  "utility", "productivity", "finance", "communication"
]

const actionTypeIcons = {
  REST: Globe,
  DATABASE: Database,
  CODE_RUN: Code,
  KNOWLEDGE_BASE: BookOpen,
}

interface TestVariable {
  name: string
  value: string
  required?: boolean
  type?: string
}

export default function ActionEditPage() {
  const params = useParams()
  const router = useRouter()
  const { workspaceId, isReady } = useWorkspaceReady()
  const actionId = params.actionId as string
  
  // Load action and secrets using hooks
  const { data: action, isLoading: loading, error: actionError } = useAction(workspaceId || undefined, actionId)
  const { data: secrets } = useSecrets(workspaceId || undefined)
  const updateAction = useUpdateAction()
  
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResponse, setTestResponse] = useState<any>(null)
  const [lastRawResponse, setLastRawResponse] = useState<any>(null)
  const [testVariables, setTestVariables] = useState<TestVariable[]>([])

  // Form setup
  const form = useForm({
    resolver: zodResolver(actionFormSchema),
    defaultValues: {
      name: "",
      description: "",
      type: "REST",
      tags: [],
      version: "1.0.0",
      inputVariables: [],
      method: "POST",
      url: "",
      headers: [],
      bodyType: "json",
      body: "",
      responseTransformation: "{{response}}",
      requestTransformation: "",
      secretRefs: []
    }
  })

  const { fields: headerFields, append: appendHeader, remove: removeHeader } = useFieldArray({
    control: form.control,
    name: "headers"
  })

  const { fields: variableFields, append: appendVariable, remove: removeVariable } = useFieldArray({
    control: form.control,
    name: "inputVariables"
  })

  // Load action data and populate form when action is loaded
  useEffect(() => {
    if (!action) return

    // Handle headers format conversion - supports both array and dictionary formats
    const backendHeaders = (action.default_config as any)?.headers || []
    let formattedHeaders: Array<{key: string, value: string}> = []
    
    if (Array.isArray(backendHeaders)) {
      // Array format: [{key: "name", value: "value"}, ...] or [{name: "name", value: "value"}, ...]
      formattedHeaders = backendHeaders.map((header: any) => {
        if (typeof header === 'object' && header.key && header.value) {
          return { key: header.key, value: header.value }
        } else if (typeof header === 'object' && header.name && header.value) {
          return { key: header.name, value: header.value }
        } else if (Array.isArray(header) && header.length >= 2) {
          return { key: header[0], value: header[1] }
        } else {
          return { key: "", value: "" }
        }
      }).filter((h: any) => h.key || h.value)
    } else if (typeof backendHeaders === 'object' && backendHeaders !== null) {
      // Dictionary format: {Authorization: "Bearer token", "Content-Type": "application/json"}
      formattedHeaders = Object.entries(backendHeaders).map(([key, value]) => ({
        key,
        value: value as string
      }))
    }
    
    // Set form values
    form.reset({
      name: action.name,
      description: action.description || "",
      type: action.type as any,
      tags: action.tags || [],
      version: action.version || "1.0.0",
      inputVariables: (action.config_schema as any)?.inputVariables || [],
      method: (action.default_config as any)?.method || "POST",
      url: (action.default_config as any)?.url || "",
      headers: formattedHeaders,
      bodyType: (action.default_config as any)?.bodyType || "json",
      body: (action.default_config as any)?.body || "",
      responseTransformation: (action.default_config as any)?.responseTransformation || "{{response}}",
      requestTransformation: (action.default_config as any)?.requestTransformation || "",
      secretRefs: action.secret_refs || []
    })
  }, [action, form])

  // Sync test variables with input variables from form
  useEffect(() => {
    const inputVariables = form.watch("inputVariables") || []
    const newTestVariables = inputVariables.map(inputVar => {
      // Find existing test variable or create new one
      const existing = testVariables.find(testVar => testVar.name === inputVar.name)
      return {
        name: inputVar.name,
        value: existing?.value || inputVar.default_value || "",
        required: inputVar.required,
        type: inputVar.type
      }
    })
    
    // Only update if the structure has changed to avoid infinite loops
    if (JSON.stringify(newTestVariables.map(v => ({name: v.name, required: v.required, type: v.type}))) !== 
        JSON.stringify(testVariables.map(v => ({name: v.name, required: v.required, type: v.type})))) {
      setTestVariables(newTestVariables)
    }
  }, [form.watch("inputVariables"), testVariables])


  const handleAddHeader = () => {
    appendHeader({ key: "", value: "" })
  }


  const applyTransformation = (rawResponse: any, template: string): any => {
    if (!rawResponse) return null
    
    try {
      // If template is just {{response}}, return the body
      if (template.trim() === "{{response}}") {
        return rawResponse.body || rawResponse
      }
      
      // Simple template replacement
      let result = template
      
      // Replace {{response}} with the full response body
      if (rawResponse.body) {
        const bodyStr = typeof rawResponse.body === 'string' ? rawResponse.body : JSON.stringify(rawResponse.body)
        result = result.replace(/\{\{response\}\}/g, bodyStr)
      }
      
      // Replace specific field references like {{response.main.temp}}
      const fieldRegex = /\{\{([^}]+)\}\}/g
      result = result.replace(fieldRegex, (match, fieldPath) => {
        try {
          // Navigate the response data structure
          let current = rawResponse.body || rawResponse
          const parts = fieldPath.split('.')
          
          for (const part of parts) {
            if (part === "response") continue
            if (typeof current === 'object' && current !== null) {
              if (Array.isArray(current) && /^\d+$/.test(part)) {
                current = current[parseInt(part)]
              } else {
                current = current[part]
              }
            } else {
              return match // Return original if path not found
            }
          }
          return current !== undefined && current !== null ? String(current) : match
        } catch {
          return match // Return original on any error
        }
      })
      
      return result
    } catch (e) {
      // If transformation fails, return the raw response
      return rawResponse.body || rawResponse
    }
  }

  const handleTransformationChange = async () => {
    if (lastRawResponse) {
      const newTransformation = form.getValues('responseTransformation') || '{{response}}'
      
      try {
        // Send the transformation to backend for proper Liquid rendering
        const token = await import('@/lib/auth/token-manager').then(m => m.tokenManager.getToken())
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/api/v1/workspaces/${workspaceId}/actions/${actionId}/transform`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            raw_response: lastRawResponse,
            transformation_template: newTransformation
          })
        })
        
        if (response.ok) {
          const result = await response.json()
          setTestResponse((prev: any) => ({
            ...prev,
            transformed_response: result.transformed_response,
            transformation_template: newTransformation
          }))
        } else {
          // Fallback to simple transformation if backend call fails
          const transformed = applyTransformation(lastRawResponse, newTransformation)
          setTestResponse((prev: any) => ({
            ...prev,
            transformed_response: transformed,
            transformation_template: newTransformation
          }))
        }
      } catch (error) {
        // Fallback to simple transformation if backend call fails
        const transformed = applyTransformation(lastRawResponse, newTransformation)
        setTestResponse((prev: any) => ({
          ...prev,
          transformed_response: transformed,
          transformation_template: newTransformation
        }))
      }
    }
  }

  const handleTestAction = async () => {
    if (!action) return
    
    // Validate required test variables
    const missingRequired = testVariables.filter(v => v.required && (!v.value || v.value.trim() === ''))
    if (missingRequired.length > 0) {
      toast.error(`Please provide values for required variables: ${missingRequired.map(v => v.name).join(', ')}`)
      return
    }
    
    setTesting(true)
    try {
      // Create test payload with variables
      const variables = testVariables.reduce((acc, v) => {
        if (v.name && v.value) {
          acc[v.name] = v.value
        }
        return acc
      }, {} as Record<string, string>)
      
      // Get current form values for configuration
      const formValues = form.getValues()
      const currentConfig = {
        url: formValues.url,
        method: formValues.method,
        headers: formValues.headers,
        body: formValues.body
      }
      
      // Create test input with current configuration and transformation
      const testInputWithConfig = {
        test_variables: variables,
        current_config: currentConfig,
        current_transformation: form.getValues('responseTransformation') || '{{response}}'
      }

      const response = await protoboxClient.executeAction(workspaceId || undefined, actionId, testInputWithConfig)
      
      // Handle both success and error responses from the new backend
      if (response.data) {
        const data = response.data as any
        
        // Check if it's an error response from the backend
        if (data.success === false) {
          const errorResult = {
            status: 'error',
            timestamp: new Date().toISOString(),
            success: false,
            error_message: data.error_message || 'Unknown error occurred',
            error_type: data.error_type || 'UnknownError',
            execution_time_ms: data.execution_time_ms || 0,
            test_input: data.test_input || variables,
            raw_response: data.raw_response || null,
            transformed_response: data.transformed_response || null,
            transformation_template: data.transformation_template || form.getValues('responseTransformation'),
            traceback: data.traceback || null
          }
          
          setTestResponse(errorResult)
          toast.error(`Test failed: ${data.error_message}`)
        } else {
          // Success response with actual API data
          const rawApiResponse = data.raw_response || data
          const currentTransformation = form.getValues('responseTransformation') || '{{response}}'
          
          // Use backend's transformed response if available, otherwise apply local transformation
          const transformed = data.transformed_response !== undefined 
            ? data.transformed_response 
            : applyTransformation(rawApiResponse, currentTransformation)
          
          const successResult = {
            status: 'success',
            timestamp: new Date().toISOString(),
            success: true,
            execution_time_ms: data.execution_time_ms || 0,
            test_input: data.test_input || variables,
            raw_response: rawApiResponse,
            transformed_response: transformed,
            transformation_template: data.transformation_template || currentTransformation,
            http_status: rawApiResponse?.status_code,
            response_headers: rawApiResponse?.headers
          }
          
          // Store the raw response for future transformations
          setLastRawResponse(rawApiResponse)
          setTestResponse(successResult)
          toast.success('Action tested successfully')
        }
      } else {
        throw new Error('No response data received')
      }
    } catch (error: any) {
      
      // Handle network/client errors
      let errorMessage = 'Unknown error'
      let errorDetails = error
      
      if (error.response?.data) {
        // Server returned an error response
        const serverError = error.response.data
        errorMessage = serverError.error_message || serverError.detail || serverError.message || 'Server error'
        errorDetails = serverError
      } else if (error.message) {
        errorMessage = error.message
      }
      
      const errorResponse = {
        status: 'error',
        timestamp: new Date().toISOString(),
        success: false,
        error_message: errorMessage,
        error_type: error.name || 'ClientError',
        execution_time_ms: 0,
        test_input: testVariables.reduce((acc, v) => {
          if (v.name && v.value) acc[v.name] = v.value
          return acc
        }, {} as Record<string, string>),
        error_details: errorDetails,
        transformation_template: form.getValues('responseTransformation')
      }
      
      setTestResponse(errorResponse)
      toast.error(`Test failed: ${errorMessage}`)
    } finally {
      setTesting(false)
    }
  }

  const onSubmit = async (data: ActionFormData) => {
    setSaving(true)
    try {
      const updateData = {
        name: data.name,
        description: data.description,
        version: data.version,
        tags: data.tags,
        config_schema: {
          inputVariables: data.inputVariables
        },
        default_config: {
          method: data.method,
          url: data.url,
          headers: data.headers.filter(h => h.key || h.value),
          bodyType: data.bodyType,
          body: data.body,
          responseTransformation: data.responseTransformation,
          requestTransformation: data.requestTransformation,
        },
        secret_refs: data.secretRefs
      }

      await updateAction.mutateAsync({
        actionId,
        data: updateData,
      })
      toast.success('Action updated successfully')
      router.push(`/workspace/${workspaceId}/dashboard/actions`)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update action')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading action...</p>
        </div>
      </div>
    )
  }

  if (actionError || !action) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">Action not found</p>
          <Button onClick={() => router.push(`/workspace/${workspaceId || ''}/dashboard/actions`)}>
            Back to Actions
          </Button>
        </div>
      </div>
    )
  }

  const Icon = actionTypeIcons[form.watch("type") as keyof typeof actionTypeIcons] || Settings

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Icon className="h-8 w-8 text-muted-foreground" />
          <div>
            <h1 className="text-3xl font-bold">
              {action && form.watch("method") && form.watch("type") === "REST" 
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
          <Button onClick={handleTestAction} disabled={testing} variant="outline">
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
          <Button type="submit" form="action-form" disabled={saving}>
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
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* Main Form - Left Column */}
        <div className="col-span-8 space-y-6">
          <Form {...form}>
            <form id="action-form" onSubmit={form.handleSubmit(onSubmit as any)} className="space-y-6">
              {/* Basic Information */}
              <Card>
                <CardHeader>
                  <CardTitle>Basic Information</CardTitle>
                  <CardDescription>
                    Configure the basic properties of your action
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Name</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g., Get Weather Data" {...field} />
                          </FormControl>
                          <FormDescription>
                            A unique, descriptive name for your action. Use letters, numbers, spaces, hyphens, and underscores only.
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="version"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Version</FormLabel>
                          <FormControl>
                            <Input placeholder="1.0.0" {...field} />
                          </FormControl>
                          <FormDescription>
                            Semantic version following MAJOR.MINOR.PATCH format. Increment when making changes.
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  
                  <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Description</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Fetches current weather data for a given city using OpenWeatherMap API"
                            rows={3}
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Detailed explanation of what this action does and when to use it. This helps AI assistants understand the purpose.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <FormField
                    control={form.control}
                    name="tags"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Tags</FormLabel>
                        <FormControl>
                          <TagsInput
                            value={field.value}
                            onChange={field.onChange}
                            placeholder="e.g., weather, api, external"
                            suggestions={commonTags}
                          />
                        </FormControl>
                        <FormDescription>
                          Add tags to categorize and filter actions. Start typing to see suggestions, or press Enter to add custom tags.
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </CardContent>
              </Card>

              {/* Input Variables */}
              <Card>
                <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-4">
                  <div className="space-y-1">
                    <CardTitle>Input Variables</CardTitle>
                    <CardDescription>
                      Define variables that the LLM will ask users to provide when using this action
                    </CardDescription>
                  </div>
                  <Button 
                    type="button"
                    onClick={() => appendVariable({ name: "", description: "", type: "string", required: true })}
                    size="sm" 
                    className="shrink-0"
                  >
                    <Plus className="w-4 h-4" />
                  </Button>
                </CardHeader>
                <CardContent className="space-y-4">
                  {variableFields.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      No variables configured. Click "+" to add variables.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {/* Header row */}
                      <div className="grid grid-cols-12 gap-4 text-sm font-medium text-muted-foreground border-b pb-2">
                        <div className="col-span-3">Name</div>
                        <div className="col-span-4">Description</div>
                        <div className="col-span-2">Type</div>
                        <div className="col-span-2">Required</div>
                        <div className="col-span-1">Actions</div>
                      </div>

                      {/* Variable rows */}
                      {variableFields.map((field, index) => (
                        <div key={field.id} className="grid grid-cols-12 gap-4 items-center py-1">
                          <div className="col-span-3">
                            <FormField
                              control={form.control}
                              name={`inputVariables.${index}.name`}
                              render={({ field }) => (
                                <FormItem>
                                  <FormControl>
                                    <Input placeholder="city" {...field} />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>
                          <div className="col-span-4">
                            <FormField
                              control={form.control}
                              name={`inputVariables.${index}.description`}
                              render={({ field }) => (
                                <FormItem>
                                  <FormControl>
                                    <Input placeholder="The city to get weather for" {...field} />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>
                          <div className="col-span-2">
                            <FormField
                              control={form.control}
                              name={`inputVariables.${index}.type`}
                              render={({ field }) => (
                                <FormItem>
                                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                                    <FormControl>
                                      <SelectTrigger>
                                        <SelectValue placeholder="Type" />
                                      </SelectTrigger>
                                    </FormControl>
                                    <SelectContent>
                                      <SelectItem value="string">String</SelectItem>
                                      <SelectItem value="number">Number</SelectItem>
                                      <SelectItem value="boolean">Boolean</SelectItem>
                                    </SelectContent>
                                  </Select>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>
                          <div className="col-span-2">
                            <div className="flex items-center space-x-2">
                              <FormField
                                control={form.control}
                                name={`inputVariables.${index}.required`}
                                render={({ field }) => (
                                  <FormItem>
                                    <FormControl>
                                      <Checkbox
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                      />
                                    </FormControl>
                                    <FormMessage />
                                  </FormItem>
                                )}
                              />
                            </div>
                          </div>
                          <div className="col-span-1">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => removeVariable(index)}
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  <div className="text-sm text-muted-foreground">
                    <p>Variables can be used in URLs with <code>{'{variable_name}'}</code> and in request bodies with <code>{'{{variable_name}}'}</code>.</p>
                  </div>
                </CardContent>
              </Card>

              {/* REST API Configuration */}
              {form.watch("type") === "REST" && (
                <Card>
                  <CardHeader>
                    <CardTitle>REST API Configuration</CardTitle>
                    <CardDescription>
                      Configure the HTTP request details
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Method and URL in single row */}
                    <div className="space-y-2">
                      {/* Header row */}
                      <div className="grid grid-cols-12 gap-4 text-sm font-medium text-muted-foreground border-b pb-2">
                        <div className="col-span-2">Method</div>
                        <div className="col-span-10">URL</div>
                      </div>
                      
                      {/* Method and URL row */}
                      <div className="grid grid-cols-12 gap-4 items-start">
                        <div className="col-span-2">
                          <FormField
                            control={form.control}
                            name="method"
                            render={({ field }) => (
                              <FormItem>
                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                  <FormControl>
                                    <SelectTrigger>
                                      <SelectValue />
                                    </SelectTrigger>
                                  </FormControl>
                                  <SelectContent>
                                    {httpMethods.map((method) => (
                                      <SelectItem key={method} value={method}>
                                        {method}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>
                        <div className="col-span-10">
                          <FormField
                            control={form.control}
                            name="url"
                            render={({ field }) => (
                              <FormItem>
                                <FormControl>
                                  <Input
                                    placeholder="https://api.openweathermap.org/data/2.5/weather?q={{city}}&appid={{api_key}}"
                                    {...field}
                                  />
                                </FormControl>
                                <FormDescription>
                                  The complete URL for the API endpoint. Use variables like {'{{city}}'} for dynamic values.
                                </FormDescription>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        </div>
                      </div>
                    </div>

                    <Card>
                      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-4">
                        <div className="space-y-1">
                          <CardTitle>Headers</CardTitle>
                          <CardDescription>
                            HTTP headers to include with requests. Common examples: Authorization, Content-Type, X-API-Key.
                          </CardDescription>
                        </div>
                        <Button 
                          type="button" 
                          onClick={handleAddHeader} 
                          size="sm" 
                          className="shrink-0"
                        >
                          <Plus className="w-4 h-4" />
                        </Button>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {headerFields.length === 0 ? (
                          <div className="text-center py-8 text-muted-foreground">
                            No headers configured. Click "+" to add headers.
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {/* Header row */}
                            <div className="grid grid-cols-12 gap-4 text-sm font-medium text-muted-foreground border-b pb-2">
                              <div className="col-span-5">Header Name</div>
                              <div className="col-span-6">Header Value</div>
                              <div className="col-span-1">Actions</div>
                            </div>
                            
                            {/* Header rows */}
                            {headerFields.map((field, index) => (
                              <div key={field.id} className="grid grid-cols-12 gap-4 items-center">
                                <div className="col-span-5">
                                  <FormField
                                    control={form.control}
                                    name={`headers.${index}.key`}
                                    render={({ field }) => (
                                      <FormItem>
                                        <FormControl>
                                          <Input placeholder="Authorization" {...field} />
                                        </FormControl>
                                      </FormItem>
                                    )}
                                  />
                                </div>
                                <div className="col-span-6">
                                  <FormField
                                    control={form.control}
                                    name={`headers.${index}.value`}
                                    render={({ field }) => (
                                      <FormItem>
                                        <FormControl>
                                          <Input placeholder="Bearer {{api_token}}" {...field} />
                                        </FormControl>
                                      </FormItem>
                                    )}
                                  />
                                </div>
                                <div className="col-span-1">
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={() => removeHeader(index)}
                                    className="text-destructive hover:text-destructive"
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </Button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>

                    <FormField
                      control={form.control}
                      name="bodyType"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Body Type</FormLabel>
                          <Select onValueChange={field.onChange} defaultValue={field.value}>
                            <FormControl>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {bodyTypes.map((type) => (
                                <SelectItem key={type.value} value={type.value}>
                                  {type.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <FormDescription>
                            Format of the request body. JSON is most common for modern APIs. Use variables like {'{{city}}'} in the body.
                          </FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {form.watch("bodyType") !== "none" && (
                      <FormField
                        control={form.control}
                        name="body"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Request Body</FormLabel>
                            <FormControl>
                              <Textarea
                                placeholder={
                                  form.watch("bodyType") === "json" 
                                    ? '{\n  "q": "{{city}}",\n  "appid": "{{api_key}}",\n  "units": "metric"\n}'
                                    : "Request body content with variables like {{variable_name}}"
                                }
                                rows={6}
                                className="font-mono"
                                {...field}
                              />
                            </FormControl>
                            <FormDescription>
                              The request body content. Use template variables like {'{{city}}'} that will be replaced with actual values during execution.
                            </FormDescription>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Transformations */}
              <Card>
                <CardHeader>
                  <CardTitle>Transformations</CardTitle>
                  <CardDescription>
                    Transform requests and responses for better AI interaction
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="response" className="w-full">
                    <TabsList className="grid w-full grid-cols-2">
                      <TabsTrigger value="request">Request Transformation</TabsTrigger>
                      <TabsTrigger value="response">Response Transformation</TabsTrigger>
                    </TabsList>
                    
                    <TabsContent value="request" className="space-y-4">
                      <FormField
                        control={form.control}
                        name="requestTransformation"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Request Transformation Template</FormLabel>
                            <FormControl>
                              <LiquidEditor
                                value={field.value || ''}
                                onChange={(value) => field.onChange(value || '')}
                                placeholder='{
  "customer_name": "{{ meeting_with | default: "Meeting" }}",
  "datetime": "{{ date | iso_datetime: time }}",
  "end_datetime": "{{ datetime | add_minutes: duration_minutes }}"
}'
                                height="250px"
                              />
                            </FormControl>
                            <FormDescription>
                              Transform natural language inputs into API-ready parameters. This Liquid template should return valid JSON.
                              Useful for converting "tomorrow afternoon" to ISO datetime format.
                            </FormDescription>
                            <div className="mt-2 text-sm text-muted-foreground">
                              <p>Available filters: <code>parse_date</code>, <code>iso_datetime</code>, <code>add_minutes</code></p>
                              <p>Example inputs: <code>when: "tomorrow"</code>, <code>time_preference: "afternoon"</code></p>
                            </div>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </TabsContent>
                    
                    <TabsContent value="response" className="space-y-4">
                      <FormField
                        control={form.control}
                        name="responseTransformation"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Response Transformation Template</FormLabel>
                            <FormControl>
                              <LiquidEditor
                                value={field.value || ''}
                                onChange={(value) => {
                                  field.onChange(value || '')
                                  // Auto-apply transformation if we have a raw response
                                  setTimeout(() => handleTransformationChange(), 100)
                                }}
                                placeholder="The temperature in {{response.name}} is {{response.main.temp}}°C with {{response.weather.0.description}}"
                                height="200px"
                              />
                            </FormControl>
                            <FormDescription>
                              Transform the API response for the AI assistant. Use <code>{'{{response.main.temp}}'}</code> to extract temperature, or <code>{'{{response}}'}</code> for the full response. 
                              Example: "The temperature in {'{{response.name}}'} is {'{{response.main.temp}}'} degrees." Changes apply automatically when testing data is available.
                            </FormDescription>
                            <div className="mt-2 text-sm text-muted-foreground">
                              <p>Supports Liquid template syntax with conditionals: <code>{'{% if success %}...{% else %}...{% endif %}'}</code>, loops: <code>{'{% for item in array %}...{% endfor %}'}</code>, and variables: <code>{'{{status_code}}'}</code>, <code>{'{{headers.date}}'}</code>.</p>
                              <a 
                                href="https://shopify.github.io/liquid/basics/introduction/"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline"
                              >
                                Learn more about Liquid templates
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            </div>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>

              {/* Secrets */}
              {secrets && secrets.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Secrets</CardTitle>
                    <CardDescription>
                      Select secrets that this action can access
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <FormField
                      control={form.control}
                      name="secretRefs"
                      render={({ field }) => (
                        <FormItem>
                          <div className="grid grid-cols-2 gap-2">
                            {(secrets || []).map((secret) => (
                              <div key={secret.id} className="flex items-center space-x-2">
                                <Checkbox
                                  checked={field.value?.includes(secret.id) || false}
                                  onCheckedChange={(checked) => {
                                    const updatedRefs = checked
                                      ? [...(field.value || []), secret.id]
                                      : (field.value || []).filter((id) => id !== secret.id)
                                    field.onChange(updatedRefs)
                                  }}
                                />
                                <Label
                                  htmlFor={`secret-${secret.id}`}
                                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                >
                                  {secret.name}
                                </Label>
                              </div>
                            ))}
                          </div>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </CardContent>
                </Card>
              )}

            </form>
          </Form>
        </div>

        {/* Testing Sidebar - Right Column */}
        <div className="col-span-4">
          <Card className="sticky top-6">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  <div>
                    <CardTitle>Test Action</CardTitle>
                    <CardDescription>
                      Test your action with variables and see the response
                    </CardDescription>
                  </div>
                </div>
                <Button onClick={handleTestAction} disabled={testing} size="sm">
                  {testing ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Test Variables */}
              <div>
                <Label className="text-sm font-medium">Test Variables</Label>
                <p className="text-xs text-muted-foreground mt-1 mb-2">
                  Define variables to test your action. These will replace {'{{variable_name}}'} in your URL, headers, and body.
                </p>
                <div className="space-y-2 mt-2">
                  {testVariables.map((variable, index) => (
                    <div key={index} className="grid grid-cols-5 gap-2">
                      <Input
                        placeholder="city"
                        value={variable.name}
                        onChange={(e) => {
                          const updated = [...testVariables]
                          updated[index] = { ...updated[index], name: e.target.value }
                          setTestVariables(updated)
                        }}
                        className="col-span-2"
                      />
                      <Input
                        placeholder="London"
                        value={variable.value}
                        onChange={(e) => {
                          const updated = [...testVariables]
                          updated[index] = { ...updated[index], value: e.target.value }
                          setTestVariables(updated)
                        }}
                        className="col-span-2"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setTestVariables(prev => prev.filter((_, i) => i !== index))
                        }}
                        disabled={testVariables.length <= 1}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>

              <Separator />

              {/* Test Results */}
              <div>
                <Label className="text-sm font-medium">Test Results</Label>
                <p className="text-xs text-muted-foreground mt-1 mb-2">
                  Raw API response and transformed output. Edit the transformation template above to see changes instantly.
                </p>
                {testResponse ? (
                  <div className="mt-2 space-y-3">
                    {/* Execution Summary */}
                    <div className="bg-muted p-2 rounded text-xs">
                      <div className="flex justify-between items-center">
                        <span className={`font-medium ${testResponse.success ? 'text-green-600' : 'text-red-600'}`}>
                          {testResponse.success ? '✅ Success' : '❌ Failed'}
                        </span>
                        <span className="text-muted-foreground">
                          {testResponse.execution_time_ms}ms
                        </span>
                      </div>
                      {testResponse.http_status && (
                        <div className="text-muted-foreground">
                          HTTP {testResponse.http_status}
                        </div>
                      )}
                    </div>

                    {testResponse.success ? (
                      <>
                        {/* Raw Response */}
                        <div>
                          <Label className="text-xs font-medium text-muted-foreground mb-1 block">Raw API Response</Label>
                          <div className="bg-slate-50 border p-2 rounded text-xs max-h-48 overflow-auto">
                            <pre className="whitespace-pre-wrap">
                              {JSON.stringify(testResponse.raw_response?.body || testResponse.raw_response, null, 2)}
                            </pre>
                          </div>
                        </div>

                        {/* Transformed Response */}
                        <div>
                          <Label className="text-xs font-medium text-muted-foreground mb-1 block">Transformed Response</Label>
                          <div className="bg-green-50 border border-green-200 p-2 rounded text-xs max-h-32 overflow-auto">
                            <pre className="whitespace-pre-wrap">
                              {typeof testResponse.transformed_response === 'string' 
                                ? testResponse.transformed_response 
                                : JSON.stringify(testResponse.transformed_response, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </>
                    ) : (
                      /* Error Response */
                      <div>
                        <Label className="text-xs font-medium text-red-600 mb-1 block">Error Details</Label>
                        <div className="bg-red-50 border border-red-200 p-2 rounded text-xs max-h-48 overflow-auto">
                          <div className="font-medium text-red-800 mb-1">{testResponse.error_type}</div>
                          <div className="text-red-700">{testResponse.error_message}</div>
                          {testResponse.raw_response && (
                            <details className="mt-2">
                              <summary className="cursor-pointer text-red-600">Raw Error Response</summary>
                              <pre className="whitespace-pre-wrap mt-1 text-red-600">
                                {JSON.stringify(testResponse.raw_response, null, 2)}
                              </pre>
                            </details>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Zap className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Click the test button to see the response</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}