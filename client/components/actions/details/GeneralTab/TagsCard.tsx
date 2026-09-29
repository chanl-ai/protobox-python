"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { TagsInput } from "@/components/ui/tags-input"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { useActionForm } from "../FormProvider"

// Common tag suggestions for actions
const commonTags = [
  "api", "external", "weather", "data", "search", "ai", "ml", "database", 
  "auth", "payment", "email", "notification", "analytics", "monitoring",
  "integration", "webhook", "social", "media", "content", "security",
  "utility", "productivity", "finance", "communication"
]

export function TagsCard() {
  const { form } = useActionForm()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tags</CardTitle>
        <CardDescription>
          Add tags to categorize and organize your actions
        </CardDescription>
      </CardHeader>
      <CardContent>
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
  )
}