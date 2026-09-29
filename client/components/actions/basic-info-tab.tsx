"use client"

import { useFieldArray } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { TagsInput } from "@/components/ui/tags-input"
import { Checkbox } from "@/components/ui/checkbox"
import { Plus, Trash2 } from "lucide-react"

// Common tag suggestions for actions
const commonTags = [
  "api", "external", "weather", "data", "search", "ai", "ml", "database", 
  "auth", "payment", "email", "notification", "analytics", "monitoring",
  "integration", "webhook", "social", "media", "content", "security",
  "utility", "productivity", "finance", "communication"
]

interface BasicInfoTabProps {
  form: any // We'll type this properly later
}

export function BasicInfoTab({ form }: BasicInfoTabProps) {
  const { fields: variableFields, append: appendVariable, remove: removeVariable } = useFieldArray({
    control: form.control,
    name: "inputVariables"
  })

  return (
    <div className="space-y-6">
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
    </div>
  )
}