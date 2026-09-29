"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { Form, FormField, FormItem, FormMessage } from "@/components/ui/form"
import { useActionForm } from "../FormProvider"
import { useWorkspaceReady } from "@/hooks"
import { useSecrets, type Secret } from "@/lib/api/hooks"

export function SecretsCard() {
  const { form } = useActionForm()
  const { workspaceId } = useWorkspaceReady()
  const { data: secrets, isLoading: loading } = useSecrets(workspaceId || undefined)

  if (loading || !secrets || secrets.length === 0) {
    return null // Don't show card if no secrets or still loading
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Secrets</CardTitle>
        <CardDescription>
          Select secrets that this action can access
        </CardDescription>
      </CardHeader>
      <CardContent>
        <FormField
          control={form.control}
          name="secretRefs"
          render={({ field }) => (
            <FormItem>
              <div className="grid grid-cols-2 gap-2">
                {secrets.map((secret) => (
                  <div key={secret.id} className="flex items-center space-x-2">
                    <Checkbox
                      checked={field.value?.includes(secret.id) || false}
                      onCheckedChange={(checked) => {
                        const updatedRefs = checked
                          ? [...(field.value || []), secret.id]
                          : (field.value || []).filter((id) => id !== secret.id)
                        field.onChange(updatedRefs)
                      }}
                    />
                    <Label
                      htmlFor={`secret-${secret.id}`}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {secret.name}
                    </Label>
                  </div>
                ))}
              </div>
              <FormMessage />
            </FormItem>
          )}
        />
      </CardContent>
    </Card>
  )
}