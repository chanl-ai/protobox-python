"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { useFieldArray } from "react-hook-form"
import { Plus, Trash2 } from "lucide-react"
import { useActionForm } from "../FormProvider"

const httpMethods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

export function EndpointCard() {
  const { form } = useActionForm()
  
  const { fields: headerFields, append: appendHeader, remove: removeHeader } = useFieldArray({
    control: form.control,
    name: "headers"
  })

  const handleAddHeader = () => {
    appendHeader({ key: "", value: "" })
  }

  return (
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

        {/* Headers Card */}
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
      </CardContent>
    </Card>
  )
}