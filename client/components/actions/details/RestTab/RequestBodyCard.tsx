"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { useActionForm } from "../FormProvider"

const bodyTypes = [
  { value: "none", label: "None" },
  { value: "json", label: "JSON" },
  { value: "form", label: "Form Data" },
  { value: "text", label: "Raw Text" }
]

export function RequestBodyCard() {
  const { form } = useActionForm()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Request Body</CardTitle>
        <CardDescription>
          Configure the request body type and content
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
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
  )
}