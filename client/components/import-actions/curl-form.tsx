"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { ChevronDown, ChevronUp } from "lucide-react"

interface CurlFormProps {
  form: {
    curlCommand: string
    name: string
    description: string
    tags: string
  }
  setForm: (updater: (prev: any) => any) => void
  showAdvanced: boolean
  setShowAdvanced: (show: boolean) => void
}

export function CurlForm({ form, setForm, showAdvanced, setShowAdvanced }: CurlFormProps) {
  return (
    <div className="space-y-4">
      <h4 className="font-medium">cURL Command</h4>
      
      {/* Required Field */}
      <div className="space-y-2">
        <Label htmlFor="curl-command">cURL Command</Label>
        <Textarea
          id="curl-command"
          placeholder="curl -X POST https://api.example.com/users -H 'Content-Type: application/json' -d '{&quot;name&quot;:&quot;John&quot;}'"
          value={form.curlCommand}
          onChange={(e) => setForm(prev => ({ ...prev, curlCommand: e.target.value }))}
          rows={4}
          className="font-mono text-sm min-h-[100px] max-h-[300px] resize-y"
        />
        <p className="text-xs text-muted-foreground">
          Paste your cURL command here - we'll parse it automatically
        </p>
      </div>

      {/* Advanced Options Toggle */}
      <div className="border-t pt-4">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground p-0 h-auto"
        >
          {showAdvanced ? (
            <>
              <ChevronUp className="w-4 h-4" />
              Hide advanced options
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Show advanced options
            </>
          )}
        </Button>
      </div>

      {/* Advanced Options */}
      {showAdvanced && (
        <div className="space-y-4 p-4 bg-muted/30 rounded-lg border">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="action-name">Custom Action Name</Label>
              <Input
                id="action-name"
                placeholder="Will be auto-generated from URL"
                value={form.name}
                onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Override the auto-generated name
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="curl-tags">Tags</Label>
              <Input
                id="curl-tags"
                placeholder="imported,curl,api"
                value={form.tags}
                onChange={(e) => setForm(prev => ({ ...prev, tags: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated tags
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="curl-description">Custom Description</Label>
            <Textarea
              id="curl-description"
              placeholder="Describe what this action does..."
              value={form.description}
              onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))}
              rows={2}
            />
            <p className="text-xs text-muted-foreground">
              Override the auto-generated description
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
