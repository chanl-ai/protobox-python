"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Checkbox } from "@/components/ui/checkbox"
import { Zap, Play, Loader2, X, Settings, Package, Plus } from "lucide-react"
import { Action } from "@/lib/api/hooks"
import { protoboxClient } from "@/lib/api/protobox-client"
import { useActionForm } from "./FormProvider"
import { EnvironmentWidget } from "./CodeTab/EnvironmentWidget"
import { ExecutionWidget } from "./CodeTab/ExecutionWidget"
import { useAuth } from "@/lib/auth"
import { useWorkspaceReady } from "@/hooks"
import { toast } from "sonner"

interface TestingSidebarProps {
  action: Action
}

interface TestVariable {
  name: string
  value: string
  required: boolean
  type: string
  description: string
}

export function TestingSidebar({ action }: TestingSidebarProps) {
  const { form } = useActionForm()
  const { user } = useAuth()
  const { isReady, workspaceId } = useWorkspaceReady()
  const [testing, setTesting] = useState(false)
  const [testVariables, setTestVariables] = useState<TestVariable[]>([])
  const [testResponse, setTestResponse] = useState<any>(null)

  // Initialize test variables from action's input variables
  useEffect(() => {
    if (action?.config_schema?.inputVariables) {
      const inputVars = action.config_schema.inputVariables as Array<{
        name: string
        description?: string
        type?: string
        required?: boolean
        default_value?: string
      }>
      
      const initialTestVars: TestVariable[] = inputVars.map(inputVar => ({
        name: inputVar.name || '',
        value: inputVar.default_value || '',
        required: inputVar.required || false,
        type: inputVar.type || 'string',
        description: inputVar.description || ''
      }))
      
      setTestVariables(initialTestVars)
    }
  }, [action])

  const handleTestAction = async () => {
    if (!user?.customToken || !isReady || !workspaceId) {
      toast.error("Missing required authentication or workspace information")
      return
    }

    setTesting(true)
    setTestResponse(null)
    
    try {
      // Validate required variables
      const missingRequired = testVariables.filter(v => v.required && !v.value.trim())
      if (missingRequired.length > 0) {
        toast.error(`Missing required variables: ${missingRequired.map(v => v.name).join(', ')}`)
        return
      }

      // Convert test variables to the format expected by the API
      const testInput = testVariables.reduce((acc, variable) => {
        if (variable.value.trim()) {
          let value: any = variable.value.trim()
          
          // Convert value based on type
          if (variable.type === 'number') {
            value = Number(value)
            if (isNaN(value)) {
              throw new Error(`Invalid number value for ${variable.name}: ${variable.value}`)
            }
          } else if (variable.type === 'boolean') {
            value = value.toLowerCase() === 'true' || value === '1'
          }
          
          acc[variable.name] = value
        }
        return acc
      }, {} as Record<string, any>)

      console.log('Testing action with input:', testInput)

      // Call the test endpoint
      const response = await protoboxClient.executeAction(workspaceId || undefined, action.id, {
        test_variables: testInput
      })

      if (response.data) {
        const responseData = response.data as any
        setTestResponse({
          status: 'success',
          timestamp: new Date().toISOString(),
          success: responseData.success || false,
          execution_time: responseData.execution_time || 0,
          test_input: testInput,
          result: responseData.result,
          error: responseData.error,
          raw_response: responseData
        })
        
        if (responseData.success) {
          toast.success("Action executed successfully")
        } else {
          toast.error(`Action failed: ${responseData.error || 'Unknown error'}`)
        }
      } else {
        throw new Error("No response data received")
      }
    } catch (error: any) {
      console.error('Test action error:', error)
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to test action'
      
      setTestResponse({
        status: 'error',
        success: false,
        error_message: errorMessage,
        timestamp: new Date().toISOString(),
        test_input: testVariables.reduce((acc, v) => {
          acc[v.name] = v.value
          return acc
        }, {} as Record<string, string>)
      })
      
      toast.error(errorMessage)
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="sticky top-6 h-[calc(100vh-120px)] border rounded-lg bg-card">
      <Tabs defaultValue="test" className="h-full flex flex-col">
        <div className="p-4 pb-0">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="test" className="text-xs">
              <Zap className="h-3 w-3 mr-1" />
              Test
            </TabsTrigger>
            <TabsTrigger value="settings" className="text-xs">
              <Settings className="h-3 w-3 mr-1" />
              Config
            </TabsTrigger>
            <TabsTrigger value="environment" className="text-xs">
              <Package className="h-3 w-3 mr-1" />
              Env
            </TabsTrigger>
          </TabsList>
        </div>

          {/* Test Tab */}
          <TabsContent value="test" className="flex-1 p-4 pt-2 space-y-4 overflow-auto">
            {/* Test Header with Run Button */}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-sm">Test Action</h3>
                <p className="text-xs text-muted-foreground">Run your action with test variables</p>
              </div>
              <Button onClick={handleTestAction} disabled={testing} size="sm">
                {testing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
              </Button>
            </div>

            <Separator />

            {/* Test Variables */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="text-sm font-medium">Test Variables</Label>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setTestVariables(prev => [...prev, {
                      name: "",
                      value: "",
                      required: false,
                      type: "string",
                      description: ""
                    }])
                  }}
                  className="text-xs"
                >
                  <Plus className="h-3 w-3 mr-1" />
                  Add Variable
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mb-3">
                {testVariables.length === 0 
                  ? "No input variables defined for this action. You can add custom variables above."
                  : "Provide values for the input variables that the action requires."
                }
              </p>
              
              {testVariables.length > 0 && (
                <div className="space-y-3">
                  {testVariables.map((variable, index) => (
                    <div key={index} className="border rounded-lg p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Label className="text-sm font-medium">{variable.name || 'Variable'}</Label>
                          {variable.required && (
                            <span className="text-xs text-red-600 font-medium">*</span>
                          )}
                          <span className="text-xs text-muted-foreground">({variable.type})</span>
                        </div>
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setTestVariables(prev => prev.filter((_, i) => i !== index))
                          }}
                          className="text-destructive hover:text-destructive p-1 h-6 w-6"
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </div>
                      
                      {variable.description && (
                        <p className="text-xs text-muted-foreground">{variable.description}</p>
                      )}
                      
                      <div className="space-y-2">
                        {/* Variable name input (for custom variables) */}
                        {!action?.config_schema?.inputVariables?.find((v: any) => v.name === variable.name) && (
                          <Input
                            placeholder="Variable name"
                            value={variable.name}
                            onChange={(e) => {
                              const updated = [...testVariables]
                              updated[index] = { ...updated[index], name: e.target.value }
                              setTestVariables(updated)
                            }}
                            className="text-sm"
                          />
                        )}
                        
                        {/* Value input based on type */}
                        {variable.type === 'boolean' ? (
                          <div className="flex items-center space-x-2">
                            <Checkbox
                              checked={variable.value === 'true'}
                              onCheckedChange={(checked) => {
                                const updated = [...testVariables]
                                updated[index] = { ...updated[index], value: checked ? 'true' : 'false' }
                                setTestVariables(updated)
                              }}
                            />
                            <Label className="text-sm">{variable.value === 'true' ? 'True' : 'False'}</Label>
                          </div>
                        ) : (
                          <Input
                            type={variable.type === 'number' ? 'number' : 'text'}
                            placeholder={
                              variable.type === 'number' ? '123' :
                              variable.type === 'boolean' ? 'true/false' :
                              'Enter value...'
                            }
                            value={variable.value}
                            onChange={(e) => {
                              const updated = [...testVariables]
                              updated[index] = { ...updated[index], value: e.target.value }
                              setTestVariables(updated)
                            }}
                            className="text-sm"
                          />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <Separator />

            {/* Test Results */}
            <div>
              <Label className="text-sm font-medium">Test Results</Label>
              <p className="text-xs text-muted-foreground mt-1 mb-2">
                Results from executing the action with your test variables.
              </p>
              {testResponse ? (
                <div className="mt-2 space-y-3">
                  {/* Execution Summary */}
                  <div className={`p-2 rounded text-xs ${
                    testResponse.success 
                      ? 'bg-green-50 border border-green-200' 
                      : 'bg-red-50 border border-red-200'
                  }`}>
                    <div className="flex justify-between items-center">
                      <span className={`font-medium ${
                        testResponse.success 
                          ? 'text-green-700' 
                          : 'text-red-700'
                      }`}>
                        {testResponse.success ? '✅ Success' : '❌ Failed'}
                      </span>
                      <span className="text-muted-foreground">
                        {testResponse.execution_time || 0}ms
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {new Date(testResponse.timestamp).toLocaleTimeString()}
                    </div>
                  </div>

                  {/* Test Input */}
                  <div>
                    <Label className="text-xs font-medium text-muted-foreground mb-1 block">Test Input</Label>
                    <div className="bg-slate-50 border p-2 rounded text-xs max-h-24 overflow-auto">
                      <pre className="whitespace-pre-wrap">
                        {JSON.stringify(testResponse.test_input || {}, null, 2)}
                      </pre>
                    </div>
                  </div>

                  {testResponse.success ? (
                    <>
                      {/* Result */}
                      {testResponse.result && (
                        <div>
                          <Label className="text-xs font-medium text-muted-foreground mb-1 block">Result</Label>
                          <div className="bg-green-50 border border-green-200 p-2 rounded text-xs max-h-32 overflow-auto">
                            <pre className="whitespace-pre-wrap">
                              {typeof testResponse.result === 'string' 
                                ? testResponse.result 
                                : JSON.stringify(testResponse.result, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}

                      {/* Raw Response */}
                      {testResponse.raw_response && (
                        <div>
                          <Label className="text-xs font-medium text-muted-foreground mb-1 block">Raw Response</Label>
                          <div className="bg-slate-50 border p-2 rounded text-xs max-h-24 overflow-auto">
                            <pre className="whitespace-pre-wrap">
                              {JSON.stringify(testResponse.raw_response, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    /* Error Response */
                    <div>
                      <Label className="text-xs font-medium text-red-600 mb-1 block">Error Details</Label>
                      <div className="bg-red-50 border border-red-200 p-2 rounded text-xs max-h-32 overflow-auto">
                        <div className="text-red-700 whitespace-pre-wrap">
                          {testResponse.error_message || testResponse.error || 'Unknown error occurred'}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground">
                  <Zap className="h-6 w-6 mx-auto mb-2 opacity-50" />
                  <p className="text-xs">Click the test button to see the response</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings" className="flex-1 p-4 pt-2 overflow-auto">
            <ExecutionWidget />
          </TabsContent>

          {/* Environment Tab */}
          <TabsContent value="environment" className="flex-1 p-4 pt-2 overflow-auto">
            <EnvironmentWidget />
          </TabsContent>
      </Tabs>
    </div>
  )
}