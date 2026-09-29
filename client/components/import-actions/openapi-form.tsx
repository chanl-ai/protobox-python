"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { ChevronDown, ChevronUp } from "lucide-react"

interface OpenAPIFormProps {
  form: {
    specUrl: string
    specContent: string
    baseUrlOverride: string
    includePaths: string
    excludePaths: string
    namePrefix: string
    tags: string
  }
  setForm: (updater: (prev: any) => any) => void
  showAdvanced: boolean
  setShowAdvanced: (show: boolean) => void
}

export function OpenAPIForm({ form, setForm, showAdvanced, setShowAdvanced }: OpenAPIFormProps) {
  return (
    <div className="space-y-4">
      <h4 className="font-medium">OpenAPI Specification</h4>
      
      {/* Required Fields */}
      <div className="space-y-2">
        <Label htmlFor="spec-url">OpenAPI Spec URL</Label>
        <Input
          id="spec-url"
          placeholder="https://api.example.com/openapi.json"
          value={form.specUrl}
          onChange={(e) => setForm(prev => ({ ...prev, specUrl: e.target.value }))}
        />
        <p className="text-xs text-muted-foreground">
          Or paste the spec content below
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="spec-content">OpenAPI Spec Content</Label>
        <Textarea
          id="spec-content"
          placeholder="Paste your OpenAPI spec (YAML or JSON)..."
          value={form.specContent}
          onChange={(e) => setForm(prev => ({ ...prev, specContent: e.target.value }))}
          rows={8}
          className="font-mono text-sm min-h-[200px] max-h-[400px] resize-y"
        />
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
              <Label htmlFor="base-url">Base URL Override</Label>
              <Input
                id="base-url"
                placeholder="https://api.example.com"
                value={form.baseUrlOverride}
                onChange={(e) => setForm(prev => ({ ...prev, baseUrlOverride: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Override the base URL from the spec
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="name-prefix">Name Prefix</Label>
              <Input
                id="name-prefix"
                placeholder="api-"
                value={form.namePrefix}
                onChange={(e) => setForm(prev => ({ ...prev, namePrefix: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Prefix for all action names
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="include-paths">Include Paths</Label>
              <Input
                id="include-paths"
                placeholder="/users,/posts"
                value={form.includePaths}
                onChange={(e) => setForm(prev => ({ ...prev, includePaths: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Only import these paths (comma-separated)
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="exclude-paths">Exclude Paths</Label>
              <Input
                id="exclude-paths"
                placeholder="/internal,/admin"
                value={form.excludePaths}
                onChange={(e) => setForm(prev => ({ ...prev, excludePaths: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Skip these paths (comma-separated)
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="tags">Tags</Label>
            <Input
              id="tags"
              placeholder="imported,openapi,external"
              value={form.tags}
              onChange={(e) => setForm(prev => ({ ...prev, tags: e.target.value }))}
            />
            <p className="text-xs text-muted-foreground">
              Comma-separated tags to add to all imported actions
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
