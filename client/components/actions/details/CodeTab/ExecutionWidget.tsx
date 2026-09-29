"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Settings, Clock } from "lucide-react"
import { useActionForm } from "../FormProvider"

export function ExecutionWidget() {
  const { form } = useActionForm()

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-medium text-sm">Execution Settings</h3>
        <p className="text-xs text-muted-foreground">Configure code execution parameters</p>
      </div>

      <Separator />

      {/* Deployment Environment */}
      <FormField
        control={form.control}
        name="deploymentEnvironment"
        render={({ field }) => (
          <FormItem>
            <FormLabel className="text-sm">Deployment Environment</FormLabel>
            <Select onValueChange={field.onChange} defaultValue={field.value || "development"}>
              <FormControl>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                <SelectItem value="development">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">DEV</Badge>
                    Development
                  </div>
                </SelectItem>
                <SelectItem value="staging">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-xs">STG</Badge>
                    Staging
                  </div>
                </SelectItem>
                <SelectItem value="production">
                  <div className="flex items-center gap-2">
                    <Badge variant="destructive" className="text-xs">PRD</Badge>
                    Production
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <FormDescription className="text-xs">
              Choose target environment for testing and deployment
            </FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />

      {/* Execution Timeout */}
      <FormField
        control={form.control}
        name="executionTimeout"
        render={({ field }) => (
          <FormItem>
            <FormLabel className="text-sm">Execution Timeout</FormLabel>
            <FormControl>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  min="1"
                  max="300"
                  {...field}
                  onChange={(e) => field.onChange(Number(e.target.value))}
                />
                <span className="text-xs text-muted-foreground">seconds</span>
              </div>
            </FormControl>
            <FormDescription className="text-xs">
              Maximum execution time (1-300 seconds)
            </FormDescription>
            <FormMessage />
          </FormItem>
        )}
      />
    </div>
  )
}