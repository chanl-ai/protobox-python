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
import { TagInput } from "@/components/ui/tag-input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Copy, Loader2 } from "lucide-react"
import { toast } from "sonner"

const duplicateSchema = z.object({
  name: z.string().min(1, "Name is required").max(100, "Name must be less than 100 characters"),
  description: z.string().min(1, "Description is required").max(500, "Description must be less than 500 characters"),
  category: z.string().min(1, "Category is required"),
  tags: z.array(z.string()).default([]),
})

type DuplicateFormData = z.infer<typeof duplicateSchema>

interface DuplicatePromptDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  prompt?: {
    id: string
    name: string
    description: string
    category: string
    tags: string[]
    messages: any[]
    arguments: any[]
  } | null
  onSuccess: (newPrompt: any) => void
}

const categories = [
  "Customer Service",
  "Marketing",
  "Development",
  "Content Creation",
  "Analysis",
  "Other"
]

export function DuplicatePromptDialog({ open, onOpenChange, prompt, onSuccess }: DuplicatePromptDialogProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!prompt) {
    return null
  }

  const form = useForm({
    resolver: zodResolver(duplicateSchema),
    defaultValues: {
      name: `${prompt.name} (Copy)`,
      description: prompt.description,
      category: prompt.category,
      tags: prompt.tags,
    },
  })

  const onSubmit = async (data: DuplicateFormData) => {
    setIsSubmitting(true)
    try {
      // TODO: Replace with actual API call when backend supports it
      // const response = await promptsApi.duplicatePrompt(prompt.id, data)
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      // Mock response - in real app, this would come from API
      const newPrompt = {
        id: Date.now().toString(),
        ...data,
        messages: prompt.messages,
        arguments: prompt.arguments,
        status: "Draft",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        usage_count: 0,
        created_by: "Current User",
        is_active: true,
      }
      
      onSuccess(newPrompt)
      form.reset()
      onOpenChange(false)
      toast.success("Prompt duplicated successfully")
    } catch (error) {
      toast.error("Failed to duplicate prompt")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Copy className="h-5 w-5" />
            Duplicate Prompt
          </DialogTitle>
          <DialogDescription>
            Create a copy of "{prompt.name}" with a new name and settings
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <div className="space-y-4">
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
                        placeholder="Describe what this prompt does"
                        className="min-h-[80px]"
                        {...field} 
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Category *</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
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
            </div>

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
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Duplicating...
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4 mr-2" />
                    Duplicate Prompt
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
