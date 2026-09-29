"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FormControl, FormDescription, FormField, FormItem, FormLabel } from "@/components/ui/form"
import { Textarea } from "@/components/ui/textarea"
import { useActionForm } from "../FormProvider"

export function ResponseCard() {
  const { form } = useActionForm()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Response Transformation</CardTitle>
        <CardDescription>
          Configure how the API response is processed and transformed
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="request" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="request">Request Transform</TabsTrigger>
            <TabsTrigger value="response">Response Transform</TabsTrigger>
          </TabsList>
          
          <TabsContent value="request" className="space-y-4">
            <FormField
              control={form.control}
              name="requestTransformation"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Request Transformation Template</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={`{
  "processed_request": {
    "original_body": {{ body | jsonify }},
    "timestamp": "{{ 'now' | date: '%Y-%m-%d %H:%M:%S' }}",
    "user_agent": "ProtoBox/1.0"
  }
}`}
                      rows={8}
                      className="font-mono"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Transform the request before sending it to the API. Use Liquid template syntax with variables like {'{{body}}'}, {'{{url}}'}, {'{{method}}'}.
                  </FormDescription>
                </FormItem>
              )}
            />
          </TabsContent>
          
          <TabsContent value="response" className="space-y-4">
            <FormField
              control={form.control}
              name="responseTransformation"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Response Transformation Template</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder={`{
  "summary": "{{ data.main.temp }}°C in {{ data.name }}",
  "temperature": {{ data.main.temp }},
  "description": "{{ data.weather[0].description }}",
  "city": "{{ data.name }}",
  "formatted": "The weather in {{ data.name }} is {{ data.main.temp }}°C with {{ data.weather[0].description }}"
}`}
                      rows={8}
                      className="font-mono"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Transform the API response before returning it. Use Liquid template syntax to extract and format data from the response object.
                  </FormDescription>
                </FormItem>
              )}
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}