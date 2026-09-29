"use client"

import { useState, useEffect } from "react"
import { useAuthStore } from "@/lib/auth/stores/auth.store"
import { protoboxClient } from "@/lib/api/protobox-client"
import { toast } from "@/lib/toast"
import { formatDistanceToNow } from "date-fns"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { InviteMembersDialog } from "./invite-members-dialog"
import { RemoveMemberDialog } from "./remove-member-dialog"
import {
  MoreHorizontal,
  Search,
  UserPlus,
  Shield,
  User,
  Crown,
  Mail,
  Calendar,
  Users,
  Settings,
  UserMinus,
  RefreshCw,
} from "lucide-react"

interface TeamMember {
  user_id: string
  email: string
  display_name?: string
  role: "owner" | "admin" | "member"
  joined_at: string
  invited_by?: string
}

const roleColors = {
  owner: "default",
  admin: "secondary",
  member: "outline",
} as const

const roleIcons = {
  owner: Crown,
  admin: Shield,
  member: User,
}

export function TeamMembersList() {
  const { currentWorkspace } = useAuthStore()
  const [members, setMembers] = useState<TeamMember[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [roleFilter, setRoleFilter] = useState<string>("all")
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false)
  const [removeMemberDialog, setRemoveMemberDialog] = useState<{
    open: boolean
    member?: TeamMember
  }>({ open: false })
  const [changingRole, setChangingRole] = useState<string | null>(null)

  useEffect(() => {
    if (currentWorkspace?.id) {
      loadMembers()
    }
  }, [currentWorkspace])

  const loadMembers = async () => {
    if (!currentWorkspace?.id) return

    setLoading(true)
    try {
      const response = await protoboxClient.listWorkspaceMembers(currentWorkspace.id)
      const data = response.data || []
      setMembers(data)
    } catch (error) {
      console.error("Failed to load members:", error)
      toast.error("Failed to load team members")
    } finally {
      setLoading(false)
    }
  }

  const handleRoleChange = async (member: TeamMember, newRole: "admin" | "member") => {
    if (!currentWorkspace?.id) return
    if (member.role === "owner") {
      toast.error("Cannot change owner role")
      return
    }

    setChangingRole(member.user_id)
    try {
      await protoboxClient.updateWorkspaceMemberRole(currentWorkspace.id, member.user_id, {
        role: newRole,
      })
      
      // Update local state
      setMembers(members.map(m => 
        m.user_id === member.user_id ? { ...m, role: newRole } : m
      ))
      
      toast.success(`Updated ${member.display_name || member.email}'s role to ${newRole}`)
    } catch (error) {
      console.error("Failed to update role:", error)
      toast.error("Failed to update member role")
    } finally {
      setChangingRole(null)
    }
  }

  const handleRemoveMember = async (member: TeamMember) => {
    if (!currentWorkspace?.id) return

    try {
      await protoboxClient.removeWorkspaceMember(currentWorkspace.id, member.user_id)
      setMembers(members.filter(m => m.user_id !== member.user_id))
      toast.success(`Removed ${member.display_name || member.email} from workspace`)
    } catch (error) {
      console.error("Failed to remove member:", error)
      toast.error("Failed to remove member")
    }
  }

  const filteredMembers = members.filter(member => {
    const matchesSearch = 
      member.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      member.display_name?.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesRole = roleFilter === "all" || member.role === roleFilter

    return matchesSearch && matchesRole
  })

  const getInitials = (name?: string, email?: string) => {
    if (name) {
      return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    }
    return email?.slice(0, 2).toUpperCase() || "??"
  }

  const getRoleBadge = (role: TeamMember["role"]) => {
    const Icon = roleIcons[role]
    return (
      <Badge variant={roleColors[role]} className="gap-1">
        <Icon className="h-3 w-3" />
        {role.charAt(0).toUpperCase() + role.slice(1)}
      </Badge>
    )
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Team Members</CardTitle>
          <CardDescription>Loading team members...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center space-x-4">
                <Skeleton className="h-10 w-10 rounded-full" />
                <div className="space-y-2">
                  <Skeleton className="h-4 w-[200px]" />
                  <Skeleton className="h-3 w-[150px]" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Team Members
              </CardTitle>
              <CardDescription>
                {members.length} member{members.length !== 1 ? "s" : ""} in this workspace
              </CardDescription>
            </div>
            <Button onClick={() => setInviteDialogOpen(true)}>
              <UserPlus className="mr-2 h-4 w-4" />
              Invite Members
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="mb-6 flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by name or email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                <SelectItem value="owner">Owner</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="member">Member</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="icon" onClick={loadMembers}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {/* Members Table */}
          {filteredMembers.length === 0 ? (
            <div className="text-center py-12">
              <Users className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-semibold">No members found</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {searchQuery || roleFilter !== "all"
                  ? "Try adjusting your filters"
                  : "Invite team members to start collaborating"}
              </p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Member</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Joined</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredMembers.map((member) => (
                    <TableRow key={member.user_id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <Avatar className="h-9 w-9">
                            <AvatarImage src={`https://avatar.vercel.sh/${member.email}`} />
                            <AvatarFallback>
                              {getInitials(member.display_name, member.email)}
                            </AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="font-medium">
                              {member.display_name || member.email.split("@")[0]}
                            </div>
                            <div className="flex items-center gap-1 text-sm text-muted-foreground">
                              <Mail className="h-3 w-3" />
                              {member.email}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {member.role === "owner" ? (
                          getRoleBadge(member.role)
                        ) : (
                          <Select
                            value={member.role}
                            onValueChange={(value: "admin" | "member") => 
                              handleRoleChange(member, value)
                            }
                            disabled={changingRole === member.user_id}
                          >
                            <SelectTrigger className="w-[120px]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="admin">
                                <div className="flex items-center gap-2">
                                  <Shield className="h-4 w-4" />
                                  Admin
                                </div>
                              </SelectItem>
                              <SelectItem value="member">
                                <div className="flex items-center gap-2">
                                  <User className="h-4 w-4" />
                                  Member
                                </div>
                              </SelectItem>
                            </SelectContent>
                          </Select>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm text-muted-foreground">
                          <Calendar className="h-3 w-3" />
                          {formatDistanceToNow(new Date(member.joined_at), { 
                            addSuffix: true 
                          })}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        {member.role !== "owner" && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuLabel>Actions</DropdownMenuLabel>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={() => {
                                  navigator.clipboard.writeText(member.email)
                                  toast.success("Email copied to clipboard")
                                }}
                              >
                                <Mail className="mr-2 h-4 w-4" />
                                Copy Email
                              </DropdownMenuItem>
                              {member.role !== "admin" && (
                                <DropdownMenuItem
                                  onClick={() => handleRoleChange(member, "admin")}
                                >
                                  <Shield className="mr-2 h-4 w-4" />
                                  Make Admin
                                </DropdownMenuItem>
                              )}
                              {member.role === "admin" && (
                                <DropdownMenuItem
                                  onClick={() => handleRoleChange(member, "member")}
                                >
                                  <User className="mr-2 h-4 w-4" />
                                  Make Member
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={() => setRemoveMemberDialog({
                                  open: true,
                                  member
                                })}
                              >
                                <UserMinus className="mr-2 h-4 w-4" />
                                Remove from Workspace
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Role Permissions Info */}
          <div className="mt-6 rounded-lg bg-muted/50 p-4">
            <h4 className="text-sm font-medium mb-3">Role Permissions</h4>
            <div className="space-y-2 text-xs text-muted-foreground">
              <div className="flex items-start gap-2">
                <Crown className="h-4 w-4 mt-0.5" />
                <div>
                  <span className="font-medium">Owner:</span> Full control over workspace, billing, and members
                </div>
              </div>
              <div className="flex items-start gap-2">
                <Shield className="h-4 w-4 mt-0.5" />
                <div>
                  <span className="font-medium">Admin:</span> Can manage workspace settings, actions, and invite members
                </div>
              </div>
              <div className="flex items-start gap-2">
                <User className="h-4 w-4 mt-0.5" />
                <div>
                  <span className="font-medium">Member:</span> Can view and use workspace resources
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Invite Members Dialog */}
      {currentWorkspace && (
        <InviteMembersDialog
          open={inviteDialogOpen}
          onOpenChange={setInviteDialogOpen}
          workspaceId={currentWorkspace.id}
          onSuccess={loadMembers}
        />
      )}

      {/* Remove Member Dialog */}
      {removeMemberDialog.member && currentWorkspace && (
        <RemoveMemberDialog
          open={removeMemberDialog.open}
          onOpenChange={(open) => setRemoveMemberDialog({ open })}
          member={removeMemberDialog.member}
          workspaceName={currentWorkspace.name}
          onConfirm={() => handleRemoveMember(removeMemberDialog.member!)}
        />
      )}
    </>
  )
}