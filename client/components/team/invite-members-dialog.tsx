"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
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
import { Badge } from "@/components/ui/badge"
import { protoboxClient } from "@/lib/api/protobox-client"
import { toast } from "@/lib/toast"
import { Mail, X, UserPlus, Shield, User, Copy, Check } from "lucide-react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface InviteMembersDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  workspaceId: string
  onSuccess: () => void
}

export function InviteMembersDialog({
  open,
  onOpenChange,
  workspaceId,
  onSuccess,
}: InviteMembersDialogProps) {
  const [emails, setEmails] = useState<string[]>([])
  const [emailInput, setEmailInput] = useState("")
  const [role, setRole] = useState<"admin" | "member">("member")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [inviteLink, setInviteLink] = useState("")
  const [linkCopied, setLinkCopied] = useState(false)

  const handleAddEmail = (email: string) => {
    const trimmedEmail = email.trim().toLowerCase()
    if (!trimmedEmail) return
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(trimmedEmail)) {
      toast.error("Please enter a valid email address")
      return
    }
    
    if (emails.includes(trimmedEmail)) {
      toast.error("Email already added")
      return
    }
    
    setEmails([...emails, trimmedEmail])
    setEmailInput("")
  }

  const handleEmailInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === "," || e.key === " ") {
      e.preventDefault()
      handleAddEmail(emailInput)
    }
  }

  const handleEmailInputBlur = () => {
    if (emailInput) {
      handleAddEmail(emailInput)
    }
  }

  const handlePasteEmails = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault()
    const pastedText = e.clipboardData.getData("text")
    const emailList = pastedText.split(/[,\s\n]+/).filter(Boolean)
    
    emailList.forEach(email => {
      const trimmedEmail = email.trim().toLowerCase()
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (emailRegex.test(trimmedEmail) && !emails.includes(trimmedEmail)) {
        setEmails(prev => [...prev, trimmedEmail])
      }
    })
  }

  const removeEmail = (emailToRemove: string) => {
    setEmails(emails.filter(email => email !== emailToRemove))
  }

  const handleSendInvites = async () => {
    if (emails.length === 0) {
      toast.error("Please add at least one email address")
      return
    }
    
    setLoading(true)
    try {
      // Send invitations
      await protoboxClient.inviteWorkspaceMembers(workspaceId, {
        emails,
        role,
        message: message || undefined,
      })
      
      toast.success(`Sent ${emails.length} invitation${emails.length > 1 ? 's' : ''}`)
      onSuccess()
      
      // Reset form
      setEmails([])
      setEmailInput("")
      setMessage("")
      setRole("member")
    } catch (error) {
      console.error("Failed to send invitations:", error)
      toast.error("Failed to send invitations")
    } finally {
      setLoading(false)
    }
  }

  const generateInviteLink = async () => {
    setLoading(true)
    try {
      const response = await protoboxClient.generateInviteLink(workspaceId, {
        role,
        expires_in_days: 7, // 7 days
      })
      
      const link = `${window.location.origin}/invite/${response.data?.token || response.data?.invite_link || ''}`
      setInviteLink(link)
    } catch (error) {
      console.error("Failed to generate invite link:", error)
      toast.error("Failed to generate invite link")
    } finally {
      setLoading(false)
    }
  }

  const copyInviteLink = async () => {
    try {
      await navigator.clipboard.writeText(inviteLink)
      setLinkCopied(true)
      toast.success("Invite link copied to clipboard")
      
      setTimeout(() => {
        setLinkCopied(false)
      }, 2000)
    } catch (error) {
      toast.error("Failed to copy link")
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Invite Team Members</DialogTitle>
          <DialogDescription>
            Invite people to collaborate in this workspace
          </DialogDescription>
        </DialogHeader>
        
        <Tabs defaultValue="email" className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="email">Email Invitation</TabsTrigger>
            <TabsTrigger value="link">Invite Link</TabsTrigger>
          </TabsList>
          
          <TabsContent value="email" className="space-y-4">
            {/* Email Input */}
            <div className="space-y-2">
              <Label htmlFor="emails">Email Addresses</Label>
              <div className="space-y-2">
                <Input
                  id="emails"
                  type="email"
                  placeholder="Enter email addresses (press Enter or comma to add)"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  onKeyDown={handleEmailInputKeyDown}
                  onBlur={handleEmailInputBlur}
                  onPaste={handlePasteEmails}
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  Tip: You can paste multiple emails separated by commas
                </p>
              </div>
              
              {/* Email Tags */}
              {emails.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {emails.map((email) => (
                    <Badge key={email} variant="secondary" className="gap-1">
                      <Mail className="h-3 w-3" />
                      {email}
                      <button
                        onClick={() => removeEmail(email)}
                        className="ml-1 hover:text-destructive"
                        disabled={loading}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>
            
            {/* Role Selection */}
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Select value={role} onValueChange={(value: "admin" | "member") => setRole(value)}>
                <SelectTrigger id="role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="member">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      <div>
                        <p className="font-medium">Member</p>
                        <p className="text-xs text-muted-foreground">Can view and use workspace resources</p>
                      </div>
                    </div>
                  </SelectItem>
                  <SelectItem value="admin">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4" />
                      <div>
                        <p className="font-medium">Admin</p>
                        <p className="text-xs text-muted-foreground">Can manage workspace and invite members</p>
                      </div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* Custom Message */}
            <div className="space-y-2">
              <Label htmlFor="message">Custom Message (Optional)</Label>
              <Textarea
                id="message"
                placeholder="Add a personal message to the invitation..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={3}
                disabled={loading}
                className="resize-none"
              />
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
                Cancel
              </Button>
              <Button onClick={handleSendInvites} disabled={loading || emails.length === 0}>
                <Mail className="mr-2 h-4 w-4" />
                Send {emails.length > 0 && `${emails.length} `}Invitation{emails.length !== 1 && 's'}
              </Button>
            </DialogFooter>
          </TabsContent>
          
          <TabsContent value="link" className="space-y-4">
            {/* Role Selection for Link */}
            <div className="space-y-2">
              <Label htmlFor="link-role">Default Role for Link</Label>
              <Select value={role} onValueChange={(value: "admin" | "member") => setRole(value)}>
                <SelectTrigger id="link-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="member">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      <div>
                        <p className="font-medium">Member</p>
                        <p className="text-xs text-muted-foreground">Can view and use workspace resources</p>
                      </div>
                    </div>
                  </SelectItem>
                  <SelectItem value="admin">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4" />
                      <div>
                        <p className="font-medium">Admin</p>
                        <p className="text-xs text-muted-foreground">Can manage workspace and invite members</p>
                      </div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* Generate Link Button */}
            {!inviteLink ? (
              <div className="text-center py-8">
                <UserPlus className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-sm text-muted-foreground mb-4">
                  Generate a link that anyone can use to join this workspace
                </p>
                <Button onClick={generateInviteLink} disabled={loading}>
                  Generate Invite Link
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Invite Link</Label>
                  <div className="flex gap-2">
                    <Input
                      value={inviteLink}
                      readOnly
                      className="font-mono text-xs"
                    />
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={copyInviteLink}
                    >
                      {linkCopied ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Copy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    This link will expire in 7 days
                  </p>
                </div>
                
                <div className="rounded-lg bg-muted/50 p-4">
                  <h4 className="text-sm font-medium mb-2">Share Instructions</h4>
                  <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
                    <li>Copy the link above</li>
                    <li>Share it with people you want to invite</li>
                    <li>They'll be able to join with the {role} role</li>
                    <li>You can revoke this link anytime from settings</li>
                  </ol>
                </div>
                
                <Button
                  variant="outline"
                  onClick={() => {
                    setInviteLink("")
                    generateInviteLink()
                  }}
                  className="w-full"
                >
                  Generate New Link
                </Button>
              </div>
            )}
            
            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Close
              </Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}