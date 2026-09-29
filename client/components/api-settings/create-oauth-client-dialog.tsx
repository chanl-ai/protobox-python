"use client"

import { useState } from "react"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { useToast } from "@/hooks/use-toast"
import { mcpOAuthApi, type CreateOAuthClientRequest } from "@/lib/api/mcp-oauth"
import { AVAILABLE_OAUTH_SCOPES } from "@/lib/constants/oauth-scopes"

interface CreateOAuthClientDialogProps {
  workspaceId: string  // Still needed for UI display, but not for API calls
  onSuccess: () => void
}


export function CreateOAuthClientDialog({ workspaceId, onSuccess }: CreateOAuthClientDialogProps) {
  const { toast } = useToast()
  const [open, setOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  
  // Form state
  const [clientName, setClientName] = useState("")
  const [description, setDescription] = useState("")
  const [redirectUris, setRedirectUris] = useState("https://yourapp.com/auth/callback")
  const [selectedScopes, setSelectedScopes] = useState<string[]>(["mcp:read", "mcp:execute"])
  
  const handleScopeChange = (scope: string, checked: boolean) => {
    if (checked) {
      setSelectedScopes(prev => [...prev, scope])
    } else {
      setSelectedScopes(prev => prev.filter(s => s !== scope))
    }
  }
  
  const handleCreateClient = async () => {
    if (!clientName || !redirectUris) {
      toast({
        title: "Missing required fields",
        description: "Please provide a client name and at least one redirect URI",
        variant: "destructive",
      })
      return
    }
    
    if (selectedScopes.length === 0) {
      toast({
        title: "Select at least one scope",
        description: "Please select at least one OAuth scope",
        variant: "destructive",
      })
      return
    }
    
    setCreating(true)
    try {
      const uris = redirectUris.split('\n').map(uri => uri.trim()).filter(Boolean)
      
      const response = await mcpOAuthApi.createClient(workspaceId, {
        client_name: clientName,
        description: description || undefined,
        redirect_uris: uris,
        scopes: selectedScopes,
      })
      
      // Show success with client credentials
      // Copy client ID to clipboard automatically
      try {
        await navigator.clipboard.writeText(response.client_id)
      } catch {
        // Ignore clipboard errors
      }
      
      toast({
        title: "OAuth Client Created",
        description: response.client_secret 
          ? `Client ID: ${response.client_id} | Client Secret: ${response.client_secret} (Save it - won't be shown again!)`
          : `Client ID: ${response.client_id} (Copied to clipboard)`,
        variant: "default",
      })
      
      setOpen(false)
      setClientName("")
      setDescription("")
      setRedirectUris("https://yourapp.com/auth/callback")
      setSelectedScopes(["mcp:read", "mcp:execute"])
      onSuccess()
    } catch (error) {
      toast({
        title: "Error creating OAuth client",
        description: error instanceof Error ? error.message : "Failed to create OAuth client",
        variant: "destructive",
      })
    } finally {
      setCreating(false)
    }
  }
  
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Client
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create OAuth Client</DialogTitle>
          <DialogDescription>
            Set up OAuth 2.1 authentication for AI assistants and applications
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 mt-4">
          <div>
            <Label htmlFor="client-name">Client Name *</Label>
            <Input
              id="client-name"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              placeholder="e.g., My Custom App"
              className="mt-1"
            />
          </div>
          
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this client for?"
              className="mt-1"
              rows={2}
            />
          </div>
          
          <div>
            <Label htmlFor="redirect-uris">Redirect URIs * (one per line)</Label>
            <Textarea
              id="redirect-uris"
              value={redirectUris}
              onChange={(e) => setRedirectUris(e.target.value)}
              placeholder="https://yourapp.com/auth/callback&#10;https://yourapp.vercel.app/auth/callback"
              className="mt-1 font-mono text-sm"
              rows={3}
            />
            <p className="text-xs text-muted-foreground mt-1">
              Add all URLs where users will be redirected after authorization
            </p>
          </div>
          
          <div>
            <Label>OAuth Scopes *</Label>
            <div className="space-y-3 mt-2">
              {AVAILABLE_OAUTH_SCOPES.map((scope) => (
                <div key={scope.value} className="flex items-start gap-3">
                  <Checkbox
                    id={scope.value}
                    checked={selectedScopes.includes(scope.value)}
                    onCheckedChange={(checked) => handleScopeChange(scope.value, checked as boolean)}
                  />
                  <div className="flex-1">
                    <Label htmlFor={scope.value} className="text-sm font-medium cursor-pointer">
                      {scope.label}
                    </Label>
                    <p className="text-xs text-muted-foreground">{scope.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreateClient} disabled={creating}>
            {creating ? "Creating..." : "Create Client"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}