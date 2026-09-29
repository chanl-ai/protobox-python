"use client"

import { useFieldArray } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { LiquidEditor } from "@/components/liquid-editor"
import { Plus, Trash2 } from "lucide-react"

const httpMethods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
const bodyTypes = [
  { value: "none", label: "None" },
  { value: "json", label: "JSON" },
  { value: "form", label: "Form Data" },
  { value: "text", label: "Raw Text" }
]

interface RestConfigurationProps {
  form: any // We'll type this properly later
}

export function RestConfiguration({ form }: RestConfigurationProps) {
  const { fields: headerFields, append: appendHeader, remove: removeHeader } = useFieldArray({
    control: form.control,
    name: "headers"
  })

  const handleAddHeader = () => {
    appendHeader({ key: "", value: "" })
  }

  return (
    <div className="space-y-6">
      {/* REST API Configuration */}
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

      {/* Transformations */}
      <Card>
        <CardHeader>
          <CardTitle>Transformations</CardTitle>
          <CardDescription>
            Transform request and response data using Liquid templates
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormField
            control={form.control}
            name="requestTransformation"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Request Transformation (Optional)</FormLabel>
                <FormControl>
                  <LiquidEditor
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="Transform request data before sending..."
                    height="150px"
                  />
                </FormControl>
                <FormDescription>
                  Transform input variables before making the API call. Use Liquid syntax to modify the request data.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="responseTransformation"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Response Transformation</FormLabel>
                <FormControl>
                  <LiquidEditor
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="Transform API response..."
                    height="150px"
                  />
                </FormControl>
                <FormDescription>
                  Transform the API response before returning to the LLM. Use {'{{response}}'} to access the raw response.
                  Example: {'{{response.data.weather[0].description}}'} extracts weather description.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </CardContent>
      </Card>
    </div>
  )
}