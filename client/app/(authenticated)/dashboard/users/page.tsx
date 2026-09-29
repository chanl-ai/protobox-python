import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Plus, Search, User, Users, Key, Shield, Mail, Calendar, Settings, Trash2, Edit } from "lucide-react"

export default function UsersPage() {
  // Mock data for users
  const users = [
    { 
      id: "user_1", 
      email: "john.doe@example.com", 
      name: "John Doe",
      status: "active", 
      lastLogin: "2 minutes ago", 
      apiKeys: 3,
      createdAt: "2024-01-15",
      emailVerified: true,
      provider: "firebase"
    },
    { 
      id: "user_2", 
      email: "jane.smith@example.com", 
      name: "Jane Smith",
      status: "active", 
      lastLogin: "1 hour ago", 
      apiKeys: 2,
      createdAt: "2024-01-10",
      emailVerified: true,
      provider: "firebase"
    },
    { 
      id: "user_3", 
      email: "bob.wilson@example.com", 
      name: "Bob Wilson",
      status: "inactive", 
      lastLogin: "1 week ago", 
      apiKeys: 1,
      createdAt: "2023-12-20",
      emailVerified: false,
      provider: "firebase"
    },
  ]

  const stats = [
    { title: "Total Users", value: "1,247", change: "+12 this week" },
    { title: "Active Users", value: "1,205", change: "+8 this week" },
    { title: "Email Verified", value: "98.2%", change: "+0.3% this week" },
    { title: "API Keys Issued", value: "2,847", change: "+127 this week" },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">User Management</h1>
          <p className="text-muted-foreground">Manage user accounts and authentication</p>
        </div>
        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          Invite User
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">{stat.change}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Users Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Users</CardTitle>
              <CardDescription>Manage user accounts and permissions</CardDescription>
            </div>
            <div className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input placeholder="Search users..." className="pl-9 w-64" />
              </div>
              <Select>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="suspended">Suspended</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead>API Keys</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar className="w-8 h-8">
                        <AvatarFallback>{user.name.split(' ').map(n => n[0]).join('')}</AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="font-medium">{user.name}</div>
                        <div className="text-sm text-muted-foreground flex items-center gap-1">
                          {user.emailVerified ? (
                            <><Shield className="w-3 h-3 text-green-500" /> Verified</>
                          ) : (
                            <><Mail className="w-3 h-3 text-yellow-500" /> Unverified</>
                          )}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <Badge variant={user.status === "active" ? "default" : "secondary"}>
                      {user.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{user.lastLogin}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{user.apiKeys}</Badge>
                  </TableCell>
                  <TableCell>{user.createdAt}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex gap-2 justify-end">
                      <Button variant="ghost" size="sm">
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        <Settings className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Authentication & Security */}
      <Card>
        <CardHeader>
          <CardTitle>Authentication & Security</CardTitle>
          <CardDescription>Authentication providers and security settings</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="providers" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="providers">Auth Providers</TabsTrigger>
              <TabsTrigger value="apikeys">API Keys</TabsTrigger>
              <TabsTrigger value="security">Security</TabsTrigger>
            </TabsList>
            <TabsContent value="providers" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Firebase Auth</CardTitle>
                    <CardDescription>Primary authentication provider</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4 text-green-500" />
                        <span className="text-sm">Active</span>
                      </div>
                      <Badge variant="default">Primary</Badge>
                    </div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      1,247 users authenticated
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">JWT Validation</CardTitle>
                    <CardDescription>Token-based authentication</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Key className="w-4 h-4 text-blue-500" />
                        <span className="text-sm">Enabled</span>
                      </div>
                      <Badge variant="secondary">Active</Badge>
                    </div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      2,847 active tokens
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            <TabsContent value="apikeys" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Total API Keys</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">2,847</div>
                    <div className="text-sm text-muted-foreground">+127 this week</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Active Keys</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">2,801</div>
                    <div className="text-sm text-muted-foreground">98.4% active</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Expiring Soon</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">23</div>
                    <div className="text-sm text-muted-foreground">Within 30 days</div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            <TabsContent value="security" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Multi-Factor Auth</CardTitle>
                    <CardDescription>Additional security layer</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Shield className="w-4 h-4 text-green-500" />
                        <span className="text-sm">Available</span>
                      </div>
                      <Button variant="outline" size="sm">Configure</Button>
                    </div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      234 users enabled (18.8%)
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Session Management</CardTitle>
                    <CardDescription>Active session control</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-blue-500" />
                        <span className="text-sm">Active</span>
                      </div>
                      <Button variant="outline" size="sm">Manage</Button>
                    </div>
                    <div className="mt-2 text-sm text-muted-foreground">
                      1,205 active sessions
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Recent user authentication and activity events</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <div className="flex-1">
                <div className="text-sm">john.doe@example.com logged in</div>
                <div className="text-xs text-muted-foreground">2 minutes ago</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              <div className="flex-1">
                <div className="text-sm">New API key created for jane.smith@example.com</div>
                <div className="text-xs text-muted-foreground">15 minutes ago</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
              <div className="flex-1">
                <div className="text-sm">Failed login attempt for unknown@example.com</div>
                <div className="text-xs text-muted-foreground">1 hour ago</div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <div className="flex-1">
                <div className="text-sm">Email verified for new.user@example.com</div>
                <div className="text-xs text-muted-foreground">3 hours ago</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
} 