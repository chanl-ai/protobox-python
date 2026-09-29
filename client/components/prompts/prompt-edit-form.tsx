"use client"

import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { forwardRef, useImperativeHandle, useEffect } from "react"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
// Select removed - category field removed
import { TagInput } from "@/components/ui/tag-input"
import { PromptArgument } from "@/lib/api/prompts"

const promptArgumentSchema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional().default(""),
  type: z.enum(['string', 'number', 'boolean', 'array', 'object']).default('string'),
  required: z.boolean().default(false),
  default: z.any().optional(),
})

const promptSchema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Name must be less than 100 characters"),
  description: z.string().min(1, "Description is required").max(500, "Description must be less than 500 characters"),
  content: z.string().min(1, "Prompt content is required"),
  tags: z.array(z.string()).optional().default([]),
  arguments: z.array(promptArgumentSchema).optional().default([]),
})

type PromptFormData = z.infer<typeof promptSchema>

// Categories removed - will be handled by global category system in future

interface PromptEditFormProps {
  initialData: PromptFormData
  onSubmit: (data: PromptFormData) => Promise<void>
  onCancel: () => void
  saving: boolean
  hideActions?: boolean // New prop to hide the form's action buttons
  onDirtyChange?: (dirty: boolean) => void // Callback when form dirty state changes
  onArgumentsChange?: (newArguments: PromptArgument[]) => void // Callback when arguments change
  onContentChange?: (content: string) => void // Callback when content changes
}

export interface PromptEditFormRef {
  submitForm: () => void
  setValue: (field: keyof PromptFormData, value: any) => void
  getValues: () => PromptFormData
}

export const PromptEditForm = forwardRef<PromptEditFormRef, PromptEditFormProps>(({ 
  initialData, 
  onSubmit, 
  onCancel, 
  saving,
  hideActions = false,
  onDirtyChange,
  onArgumentsChange,
  onContentChange
}, ref) => {
  const form = useForm({
    resolver: zodResolver(promptSchema),
    defaultValues: initialData,
  })

  // Track dirty state and notify parent
  const { isDirty } = form.formState
  useEffect(() => {
    onDirtyChange?.(isDirty)
  }, [isDirty, onDirtyChange])

  // Watch for arguments changes and notify parent
  const argumentsValue = form.watch("arguments")
  useEffect(() => {
    onArgumentsChange?.(argumentsValue || [])
  }, [argumentsValue, onArgumentsChange])

  // Watch for content changes and notify parent
  const contentValue = form.watch("content")
  useEffect(() => {
    onContentChange?.(contentValue || "")
  }, [contentValue, onContentChange])

  const handleSubmit = async (data: PromptFormData) => {
    await onSubmit(data)
  }

  useImperativeHandle(ref, () => ({
    submitForm: () => {
      form.handleSubmit(handleSubmit)()
    },
    setValue: (field: keyof PromptFormData, value: any) => {
      form.setValue(field, value)
    },
    getValues: () => {
      return form.getValues()
    }
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>Prompt Details</CardTitle>
        <CardDescription>
          Update the basic information and content of your prompt
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="Enter prompt name" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description *</FormLabel>
                  <FormControl>
                    <Textarea 
                      placeholder="Describe what this prompt does and when to use it"
                      className="min-h-[80px]"
                      {...field} 
                    />
                  </FormControl>
                  <FormDescription>
                    Brief description of the prompt's purpose and use cases
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="content"
              render={({ field }) => {
                // Validate braces
                const validateBraces = (content: string) => {
                  let openCount = 0
                  let i = 0
                  while (i < content.length) {
                    if (content[i] === '{' && content[i + 1] === '{') {
                      openCount++
                      i += 2
                    } else if (content[i] === '}' && content[i + 1] === '}') {
                      openCount--
                      i += 2
                      if (openCount < 0) return false
                    } else {
                      i++
                    }
                  }
                  return openCount === 0
                }
                
                const isBalanced = validateBraces(field.value || '')
                
                return (
                <FormItem>
                  <FormLabel>Prompt Content *</FormLabel>
                  <FormControl>
                    <Textarea 
                      placeholder="Enter your prompt content here. Use {{variable_name}} for arguments."
                      className="min-h-[300px] font-mono text-sm"
                      style={{
                        backgroundColor: !isBalanced ? '#fef2f2' : undefined
                      }}
                      {...field} 
                    />
                  </FormControl>
                  <FormDescription>
                    Use {`{{variable_name}}`} syntax to create arguments. They will be automatically added to the arguments list.
                  </FormDescription>
                  {!isBalanced && (
                    <p className="text-sm text-destructive mt-2">
                      ⚠️ Unbalanced braces detected. Make sure all {`{{`} have matching {`}}`}
                    </p>
                  )}
                  <FormMessage />
                </FormItem>
              )}}
            />

            <FormField
              control={form.control}
              name="tags"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Tags</FormLabel>
                  <FormControl>
                    <TagInput
                      placeholder="Add tags (press Enter or comma to add)"
                      value={field.value || []}
                      onChange={field.onChange}
                    />
                  </FormControl>
                  <FormDescription>
                    Add tags to help organize and categorize your prompts
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {!hideActions && (
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={onCancel}
                  disabled={saving}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            )}
          </form>
        </Form>
      </CardContent>
    </Card>
  )
})