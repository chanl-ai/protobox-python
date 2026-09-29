"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form"
import { useFieldArray } from "react-hook-form"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Package, Plus, Trash2, Key, Globe, Database, Zap } from "lucide-react"
import { useActionForm } from "../FormProvider"

// Mock workspace secrets data
const mockSecrets = [
  { id: "stripe_api_key", name: "Stripe API Key", type: "sensitive", icon: Key, environments: ["development", "staging", "production"] },
  { id: "database_url", name: "Database URL", type: "sensitive", icon: Database, environments: ["development", "staging", "production"] },
  { id: "api_base_url", name: "API Base URL", type: "config", icon: Globe, environments: ["development", "staging", "production"] },
  { id: "jwt_secret", name: "JWT Secret", type: "sensitive", icon: Key, environments: ["development", "staging", "production"] },
  { id: "webhook_secret", name: "Webhook Secret", type: "sensitive", icon: Zap, environments: ["development", "staging", "production"] },
  { id: "debug_enabled", name: "Debug Enabled", type: "config", icon: Package, environments: ["development", "staging", "production"] },
]

// Available packages
const availablePackages = [
  { id: "itty-router", name: "itty-router", description: "Tiny, zero-dependency router" },
  { id: "hono", name: "hono", description: "Fast, lightweight web framework" },
  { id: "miniflare", name: "miniflare", description: "Local development and testing" },
]

export function EnvironmentWidget() {
  const { form } = useActionForm()

  // Form field arrays for environment references and dependencies
  const { fields: envFields, append: appendEnv, remove: removeEnv } = useFieldArray({
    control: form.control,
    name: "environmentReferences" as any
  })

  const { fields: depFields, append: appendDep, remove: removeDep } = useFieldArray({
    control: form.control,
    name: "workerDependencies"
  })

  const handleAddEnvReference = () => {
    appendEnv({ secretId: "", envVarName: "" })
  }

  const handleToggleDependency = (packageId: string) => {
    const currentDeps = form.getValues("workerDependencies") || []
    const isSelected = currentDeps.includes(packageId)
    
    if (isSelected) {
      const newDeps = currentDeps.filter((dep: string) => dep !== packageId)
      form.setValue("workerDependencies", newDeps)
    } else {
      form.setValue("workerDependencies", [...currentDeps, packageId])
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-medium text-sm">Environment Configuration</h3>
        <p className="text-xs text-muted-foreground">Configure environment</p>
      </div>

      <Separator />

      {/* Environment Variables from Secrets */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <FormLabel className="text-sm">Environment Variables</FormLabel>
          <Button type="button" onClick={handleAddEnvReference} size="sm" variant="outline" className="h-6 px-2">
            <Plus className="h-3 w-3" />
          </Button>
        </div>
        <FormDescription className="text-xs mb-2">
          Reference workspace secrets as environment variables. Values are resolved based on deployment environment.
        </FormDescription>
        
        {envFields.length === 0 ? (
          <div className="text-center py-4 text-muted-foreground">
            <Key className="h-6 w-6 mx-auto mb-2 opacity-50" />
            <p className="text-xs">No environment variables configured</p>
            <p className="text-xs mt-1">Add references to workspace secrets</p>
          </div>
        ) : (
          <div className="space-y-2">
            {envFields.map((field, index) => (
              <div key={field.id} className="grid grid-cols-6 gap-2">
                <FormField
                  control={form.control}
                  name={`environmentReferences.${index}.envVarName` as any}
                  render={({ field }) => (
                    <FormItem className="col-span-2">
                      <FormControl>
                        <Input placeholder="ENV_VAR_NAME" {...field} className="text-xs font-mono" />
                      </FormControl>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name={`environmentReferences.${index}.secretId` as any}
                  render={({ field }) => (
                    <FormItem className="col-span-3">
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger className="text-xs">
                            <SelectValue placeholder="Select workspace secret" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {mockSecrets.map((secret) => {
                            const Icon = secret.icon
                            return (
                              <SelectItem key={secret.id} value={secret.id} className="text-xs">
                                <div className="flex items-center gap-2">
                                  <Icon className="h-3 w-3" />
                                  <span>{secret.name}</span>
                                  <Badge variant={secret.type === 'sensitive' ? 'destructive' : 'secondary'} className="text-xs">
                                    {secret.type}
                                  </Badge>
                                </div>
                              </SelectItem>
                            )
                          })}
                        </SelectContent>
                      </Select>
                    </FormItem>
                  )}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => removeEnv(index)}
                  className="h-8"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>

      <Separator />

      {/* Dependencies */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <FormLabel className="text-sm">Worker Dependencies</FormLabel>
        </div>
        <FormDescription className="text-xs mb-2">
          Select available packages for the action
        </FormDescription>
        
        <div className="grid grid-cols-1 gap-2">
          {availablePackages.map((pkg) => {
            const currentDeps = form.getValues("workerDependencies") || []
            const isSelected = currentDeps.includes(pkg.id)
            
            return (
              <div
                key={pkg.id}
                className={`p-2 border rounded cursor-pointer transition-colors ${
                  isSelected 
                    ? 'border-primary bg-primary/5 text-primary' 
                    : 'border-muted hover:border-muted-foreground/50'
                }`}
                onClick={() => handleToggleDependency(pkg.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Package className="h-3 w-3 flex-shrink-0" />
                      <span className="font-mono text-xs font-medium">{pkg.name}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{pkg.description}</p>
                  </div>
                  {isSelected && (
                    <div className="w-4 h-4 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                      <div className="w-2 h-2 rounded-full bg-white"></div>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}