"use client"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, User, Shield, Crown } from "lucide-react"
import { getAvatarInitials, getAvatarColor } from "@/lib/utils/avatar"

interface TeamMember {
  user_id: string
  email: string
  display_name?: string
  role: "owner" | "admin" | "member"
  joined_at: string
  invited_by?: string
}

interface RemoveMemberDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  member: TeamMember
  workspaceName: string
  onConfirm: () => void
}

const roleIcons = {
  owner: Crown,
  admin: Shield,
  member: User,
}

const roleBadgeVariants = {
  owner: "default" as const,
  admin: "secondary" as const,
  member: "outline" as const,
}

export function RemoveMemberDialog({
  open,
  onOpenChange,
  member,
  workspaceName,
  onConfirm,
}: RemoveMemberDialogProps) {
  if (!member) return null
  
  const RoleIcon = roleIcons[member.role]
  const initials = getAvatarInitials(member.display_name || "", member.email)
  const avatarColor = getAvatarColor(member.email)
  
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            Remove Team Member
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-4">
            <p>Are you sure you want to remove this member from the workspace?</p>
            
            <div className="rounded-lg border p-4">
              <div className="flex items-center gap-3">
                <Avatar className="h-10 w-10">
                  <AvatarImage src={`https://avatar.vercel.sh/${member.email}`} alt={member.display_name || ""} />
                  <AvatarFallback style={{ backgroundColor: avatarColor, color: 'white' }}>
                    {initials}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="font-medium">
                    {member.display_name || member.email.split("@")[0]}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {member.email}
                  </div>
                </div>
                <Badge variant={roleBadgeVariants[member.role]} className="gap-1">
                  <RoleIcon className="h-3 w-3" />
                  {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                </Badge>
              </div>
            </div>
            
            <div className="rounded-lg bg-destructive/10 p-3">
              <p className="text-sm text-destructive">
                <strong>Warning:</strong> This action will immediately revoke their access to all workspace resources including:
              </p>
              <ul className="mt-2 text-sm text-destructive list-disc list-inside space-y-1">
                <li>Actions and workflows</li>
                <li>Secrets and integrations</li>
                <li>Knowledge base documents</li>
                <li>Analytics and audit logs</li>
              </ul>
            </div>
            
            <p className="text-sm text-muted-foreground">
              You can always re-invite them later if needed.
            </p>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            Remove Member
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}