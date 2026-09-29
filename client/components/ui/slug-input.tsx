"use client"

import { useState, useEffect, useCallback } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Check, X, Loader2, AlertCircle, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import { protoboxClient } from "@/lib/api/protobox-client"
import { useDebounce } from "@/hooks/use-debounce"

interface SlugInputProps {
  value: string
  onChange: (value: string) => void
  onValidationChange?: (isValid: boolean) => void
  workspaceId: string
  workspaceName?: string
  className?: string
  disabled?: boolean
}

interface SlugValidation {
  available: boolean
  valid: boolean
  error: string | null
  suggested_alternatives: string[]
}

export function SlugInput({
  value,
  onChange,
  onValidationChange,
  workspaceId,
  workspaceName,
  className,
  disabled = false,
}: SlugInputProps) {
  const [isChecking, setIsChecking] = useState(false)
  const [validation, setValidation] = useState<SlugValidation | null>(null)
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [hasUserInteracted, setHasUserInteracted] = useState(false)
  const debouncedSlug = useDebounce(value, 500)

  // Check slug availability
  const checkSlug = useCallback(async (slug: string) => {
    if (!slug || slug.length < 3) {
      setValidation(null)
      onValidationChange?.(false)
      return
    }

    // For new workspaces, just do basic validation without API call
    if (workspaceId === 'new') {
      const isValid = /^[a-z0-9-]+$/.test(slug) && slug.length >= 3 && slug.length <= 63
      setValidation({
        available: true, // Assume available for new workspaces
        valid: isValid,
        error: isValid ? null : 'URL can only contain lowercase letters, numbers, and hyphens',
        suggested_alternatives: []
      })
      onValidationChange?.(isValid)
      return
    }

    setIsChecking(true)
    try {
      const result = await protoboxClient.checkSlug(workspaceId, slug)
      setValidation(result)
      onValidationChange?.(result.available && result.valid)
      
      // Show suggestions if slug is taken
      if (!result.available && result.suggested_alternatives.length > 0) {
        setShowSuggestions(true)
      }
    } catch (error) {
      setValidation({
        available: false,
        valid: false,
        error: "Failed to validate slug",
        suggested_alternatives: []
      })
      onValidationChange?.(false)
    } finally {
      setIsChecking(false)
    }
  }, [workspaceId, onValidationChange])

  // Auto-suggest slug based on workspace name
  const suggestSlug = useCallback(async () => {
    if (!workspaceName) return

    // For new workspaces, generate locally
    if (workspaceId === 'new') {
      const suggested = workspaceName.toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
        .slice(0, 63)
      
      onChange(suggested)
      setValidation({
        available: true,
        valid: true,
        error: null,
        suggested_alternatives: []
      })
      onValidationChange?.(true)
      setHasUserInteracted(true)
      return
    }

    setIsChecking(true)
    try {
      const result = await protoboxClient.suggestSlug(workspaceId, workspaceName)
      onChange(result.suggested_slug)
      setValidation({
        available: true,
        valid: true,
        error: null,
        suggested_alternatives: []
      })
      onValidationChange?.(true)
      setHasUserInteracted(true) // Mark as interacted when auto-generating
    } catch (error) {
    } finally {
      setIsChecking(false)
    }
  }, [workspaceId, workspaceName, onChange, onValidationChange])

  // Check slug when it changes
  useEffect(() => {
    if (debouncedSlug) {
      checkSlug(debouncedSlug)
    } else {
      setValidation(null)
      onValidationChange?.(false)
    }
  }, [debouncedSlug, checkSlug, onValidationChange])

  const handleSlugChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newSlug = e.target.value
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
    
    onChange(newSlug)
    setShowSuggestions(false)
    setHasUserInteracted(true)
  }

  const selectSuggestion = (suggestion: string) => {
    onChange(suggestion)
    setShowSuggestions(false)
    setValidation({
      available: true,
      valid: true,
      error: null,
      suggested_alternatives: []
    })
    onValidationChange?.(true)
    setHasUserInteracted(true) // Mark as interacted when selecting suggestion
  }

  const getValidationIcon = () => {
    if (isChecking) {
      return <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
    }
    
    if (!validation) return null
    
    if (validation.available && validation.valid) {
      return <Check className="h-4 w-4 text-green-500" />
    }
    
    return <X className="h-4 w-4 text-destructive" />
  }

  const getValidationMessage = () => {
    if (!validation) return null
    
    // Only show success message if user has interacted with the field
    if (validation.available && validation.valid && hasUserInteracted) {
      return (
        <p className="text-sm text-green-600">
          This URL is available!
        </p>
      )
    }
    
    if (validation.error) {
      return (
        <p className="text-sm text-destructive flex items-center gap-1">
          <AlertCircle className="h-3 w-3" />
          {validation.error}
        </p>
      )
    }
    
    return null
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor="slug-input">Workspace URL</Label>
          {workspaceName && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={suggestSlug}
              disabled={isChecking || disabled}
              className="h-7 text-xs"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Auto-generate
            </Button>
          )}
        </div>
        
        {/* Combined URL Preview and Input */}
        <div className={cn(
          "flex items-center rounded-md border px-3 py-2 text-sm",
          validation && !validation.available && "border-destructive",
          validation && validation.available && validation.valid && hasUserInteracted && "border-green-500",
          "bg-background"
        )}>
          <span className="text-muted-foreground">https://</span>
          <input
            id="slug-input"
            type="text"
            value={value}
            onChange={handleSlugChange}
            placeholder="my-workspace"
            disabled={disabled}
            className={cn(
              "flex-1 bg-transparent border-none outline-none px-1 font-medium",
              "placeholder:text-muted-foreground focus:ring-0",
              disabled && "cursor-not-allowed opacity-50"
            )}
          />
          <span className="text-muted-foreground">.{process.env.NEXT_PUBLIC_WORKSPACE_DOMAIN || "example.com"}</span>
          <div className="ml-2">
            {getValidationIcon()}
          </div>
        </div>

        {/* Validation Message */}
        {getValidationMessage()}

        {/* Suggestions */}
        {showSuggestions && validation?.suggested_alternatives && validation.suggested_alternatives.length > 0 && (
          <div className="space-y-2 p-3 rounded-md bg-muted/50 border">
            <p className="text-xs text-muted-foreground font-medium">
              Available alternatives:
            </p>
            <div className="flex flex-wrap gap-2">
              {validation.suggested_alternatives.map((suggestion) => (
                <Badge
                  key={suggestion}
                  variant="secondary"
                  className="cursor-pointer hover:bg-secondary/80"
                  onClick={() => selectSuggestion(suggestion)}
                >
                  {suggestion}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Help Text */}
        <p className="text-xs text-muted-foreground">
          Choose a unique web address for your workspace. Use lowercase letters, numbers, and hyphens only.
        </p>
      </div>
    </div>
  )
}