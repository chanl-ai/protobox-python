"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { useActionForm } from "../FormProvider"
import { Timer } from "lucide-react"

export function ExecutionCard() {
  const { form } = useActionForm()

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Timer className="h-5 w-5" />
          <div>
            <CardTitle>Execution Configuration</CardTitle>
            <CardDescription>
              Configure code execution settings and timeouts
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormField
          control={form.control}
          name="executionTimeout"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Execution Timeout (seconds)</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  min={1}
                  max={300}
                  placeholder="30"
                  {...field}
                  onChange={(e) => field.onChange(Number(e.target.value))}
                />
              </FormControl>
              <FormDescription>
                Maximum time to wait for code execution before timing out (1-300 seconds)
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        
        <div className="text-sm text-muted-foreground">
          <p className="font-medium mb-2">Additional execution features (coming soon):</p>
          <ul className="space-y-1 text-xs">
            <li>• Memory limits and resource constraints</li>
            <li>• Sandboxed execution environment</li>
            <li>• Code output capturing and logging</li>
            <li>• Error handling and stack traces</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}