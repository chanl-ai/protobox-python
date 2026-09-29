"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { TagInput } from "@/components/ui/tag-input"
import { toast } from "sonner"
import { promptsApi } from "@/lib/api/prompts"
import { useWorkspaceReady } from "@/hooks/useWorkspaceReady"

const promptSchema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Name must be less than 100 characters"),
  description: z.string().min(1, "Description is required").max(500, "Description must be less than 500 characters"),
  category: z.string().min(1, "Category is required"),
  system_message: z.string().optional(),
  user_message: z.string().min(1, "User message template is required"),
  tags: z.array(z.string()).optional().default([]),
})

type PromptFormData = z.infer<typeof promptSchema>

interface CreatePromptDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (prompt: any) => void
}

const categories = [
  "Customer Service",
  "Marketing", 
  "Development",
  "Communication",
  "Productivity",
  "Sales",
  "Content Creation",
  "Analysis",
  "Other"
]


export function CreatePromptDialog({ open, onOpenChange, onSuccess }: CreatePromptDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { workspaceId } = useWorkspaceReady()

  const form = useForm<PromptFormData>({
    resolver: zodResolver(promptSchema),
    defaultValues: {
      name: "",
      description: "",
      category: "",
      system_message: "You are a helpful assistant.",
      user_message: "",
      tags: [],
    },
  })

  const watchedTags = form.watch("tags")

  const onSubmit = async (data: PromptFormData) => {
    if (!workspaceId) {
      toast.error('Workspace not ready')
      return
    }

    setIsSubmitting(true)
    try {
      // Convert form data to API format
      const apiData = {
        name: data.name,
        description: data.description,
        category: data.category,
        tags: data.tags || [],
        messages: [
          ...(data.system_message ? [{
            role: 'system' as const,
            content: data.system_message
          }] : []),
          {
            role: 'user' as const,
            content: data.user_message
          }
        ],
        arguments: [], // Start with empty arguments, can be added later
        is_active: true
      }

      const newPrompt = await promptsApi.createPrompt(workspaceId, apiData)
      
      onSuccess(newPrompt)
      form.reset()
    } catch (error) {
      toast.error("Failed to create prompt")
    } finally {
      setIsSubmitting(false)
    }
  }


  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Prompt</DialogTitle>
          <DialogDescription>
            Create a new AI prompt to add to your workspace. Fill in the details below.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                name="category"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Category *</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select category" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {categories.map((category) => (
                          <SelectItem key={category} value={category}>
                            {category}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
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
              name="system_message"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>System Message (Optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="System instructions for the AI model (e.g., 'You are a helpful code reviewer...')"
                      className="min-h-[100px] font-mono text-sm"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Sets the behavior and role of the AI assistant
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="user_message"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>User Message Template *</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="User message template with {{variables}} for dynamic content..."
                      className="min-h-[150px] font-mono text-sm"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    The user message template. Use {'{{variable_name}}'} for dynamic content
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
                          <TagInput
                            placeholder="Add tags (press Enter or comma to add)"
                            value={field.value}
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


            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Creating..." : "Create Prompt"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
