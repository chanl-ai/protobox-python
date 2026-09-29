"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Form, FormControl, FormField, FormItem, FormMessage } from "@/components/ui/form"
import { useFieldArray } from "react-hook-form"
import { Plus, Trash2 } from "lucide-react"
import { useActionForm } from "../FormProvider"

export function InputVariablesCard() {
  const { form } = useActionForm()
  
  const { fields: variableFields, append: appendVariable, remove: removeVariable } = useFieldArray({
    control: form.control,
    name: "inputVariables"
  })

  return (
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
  )
}