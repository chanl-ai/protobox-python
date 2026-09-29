"use client"

import { useState } from "react"
import { Plus, Key, Shield, Copy, Check } from "lucide-react"
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useToast } from "@/hooks/use-toast"
import { mcpTokensApi, type CreateMCPTokenResponse } from "@/lib/api/mcp-tokens"
import {
  Alert,
  AlertDescription,
} from "@/components/ui/alert"

interface CreateMCPTokenDialogProps {
  workspaceId: string
  onSuccess: () => void
}

export function CreateMCPTokenDialog({ workspaceId, onSuccess }: CreateMCPTokenDialogProps) {
  const { toast } = useToast()
  const [open, setOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newToken, setNewToken] = useState<CreateMCPTokenResponse | null>(null)
  const [copiedItem, setCopiedItem] = useState<string | null>(null)
  
  // Form state
  const [tokenName, setTokenName] = useState("")
  const [tokenDescription, setTokenDescription] = useState("")
  const [expiresIn, setExpiresIn] = useState<string>("30")
  const [customDays, setCustomDays] = useState<string>("90")
  
  const handleCreate = async () => {
    if (!tokenName.trim()) {
      toast({
        title: "Name required",
        description: "Please provide a name for your token",
        variant: "destructive",
      })
      return
    }

    setCreating(true)
    try {
      let expiresInDays: number | null = null
      if (expiresIn === "custom") {
        expiresInDays = parseInt(customDays)
        if (isNaN(expiresInDays) || expiresInDays < 1 || expiresInDays > 365) {
          throw new Error("Custom expiration must be between 1 and 365 days")
        }
      } else if (expiresIn !== "never") {
        expiresInDays = parseInt(expiresIn)
      }

      const response = await mcpTokensApi.create(workspaceId, {
        name: tokenName,
        description: tokenDescription || undefined,
        expires_in_days: expiresInDays || undefined,
      })

      setNewToken(response)
      
      toast({
        title: "Token created",
        description: "Your MCP token has been created successfully",
      })
    } catch (error) {
      toast({
        title: "Error creating token",
        description: error instanceof Error ? error.message : "Failed to create MCP token",
        variant: "destructive",
      })
    } finally {
      setCreating(false)
    }
  }
  
  const copyToClipboard = async (text: string, itemId: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedItem(itemId)
      setTimeout(() => setCopiedItem(null), 2000)
      toast({
        title: "Copied",
        description: "Copied to clipboard",
      })
    } catch {
      toast({
        title: "Failed to copy",
        description: "Please copy manually",
        variant: "destructive",
      })
    }
  }
  
  const handleClose = () => {
    setOpen(false)
    setNewToken(null)
    setTokenName("")
    setTokenDescription("")
    setExpiresIn("30")
    setCustomDays("90")
    if (newToken) {
      onSuccess()
    }
  }
  
  return (
    <Dialog open={open} onOpenChange={(newOpen) => {
      if (!newOpen) {
        handleClose()
      } else {
        setOpen(true)
      }
    }}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Create Token
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {newToken ? "Token Created Successfully" : "Create MCP Token"}
          </DialogTitle>
          <DialogDescription>
            {newToken 
              ? "Save your token now - you won't be able to see it again!" 
              : "Create a new token for connecting AI assistants to your MCP server"}
          </DialogDescription>
        </DialogHeader>
        
        {newToken ? (
          <div className="space-y-4">
            <Alert className="border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950">
              <Shield className="h-4 w-4 text-green-600 dark:text-green-400" />
              <AlertDescription className="space-y-3">
                <div className="space-y-2">
                  <div>
                    <Label className="text-xs font-medium">Token</Label>
                    <div className="flex items-center gap-2 mt-1">
                      <code className="flex-1 p-2 bg-white dark:bg-gray-900 rounded text-sm font-mono break-all border">
                        {newToken.token}
                      </code>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => copyToClipboard(newToken.token, 'new-token')}
                      >
                        {copiedItem === 'new-token' ? (
                          <Check className="h-4 w-4 text-green-600" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <span className="font-medium">Token ID:</span>{" "}
                    <code className="font-mono text-xs">{newToken.token_id}</code>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
            
            <DialogFooter>
              <Button onClick={handleClose}>
                Done
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <>
            <div className="space-y-4">
              <div>
                <Label htmlFor="token-name">Token Name *</Label>
                <Input
                  id="token-name"
                  value={tokenName}
                  onChange={(e) => setTokenName(e.target.value)}
                  placeholder="e.g., Claude Desktop Token"
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="token-description">Description (Optional)</Label>
                <Textarea
                  id="token-description"
                  value={tokenDescription}
                  onChange={(e) => setTokenDescription(e.target.value)}
                  placeholder="What is this token used for?"
                  className="mt-1"
                  rows={2}
                />
              </div>

              <div>
                <Label htmlFor="token-expiration">Expiration</Label>
                <Select value={expiresIn} onValueChange={setExpiresIn}>
                  <SelectTrigger id="token-expiration" className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="7">7 days</SelectItem>
                    <SelectItem value="30">30 days</SelectItem>
                    <SelectItem value="90">90 days</SelectItem>
                    <SelectItem value="180">180 days</SelectItem>
                    <SelectItem value="365">1 year</SelectItem>
                    <SelectItem value="custom">Custom</SelectItem>
                    <SelectItem value="never">Never (Not recommended)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {expiresIn === "custom" && (
                <div>
                  <Label htmlFor="custom-days">Days until expiration</Label>
                  <Input
                    id="custom-days"
                    type="number"
                    min="1"
                    max="365"
                    value={customDays}
                    onChange={(e) => setCustomDays(e.target.value)}
                    className="mt-1"
                  />
                </div>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? "Creating..." : "Create Token"}
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}