import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Shield, Key, AlertTriangle, Settings, Eye, Trash2, Plus, RefreshCw, Lock, Unlock, Globe, Server } from "lucide-react"

export default function SecurityPage() {
  const securityEvents = [
    { id: "1", event: "Failed login attempt", user: "unknown@example.com", ip: "192.168.1.100", time: "2 minutes ago", severity: "high" },
    { id: "2", event: "API key created", user: "john.doe@example.com", ip: "10.0.0.15", time: "15 minutes ago", severity: "medium" },
    { id: "3", event: "Password changed", user: "jane.smith@example.com", ip: "172.16.0.5", time: "1 hour ago", severity: "low" },
    { id: "4", event: "Successful login", user: "bob.wilson@example.com", ip: "192.168.1.50", time: "2 hours ago", severity: "low" },
  ]

  const apiKeys = [
    { id: "key_1", name: "Production API", permissions: ["read", "write"], lastUsed: "2 minutes ago", expires: "Never", status: "active" },
    { id: "key_2", name: "Development", permissions: ["read"], lastUsed: "1 hour ago", expires: "2024-12-31", status: "active" },
    { id: "key_3", name: "Test Environment", permissions: ["read", "write"], lastUsed: "1 week ago", expires: "2024-06-15", status: "expired" },
  ]

  const stats = [
    { title: "Active Sessions", value: "1,205", change: "+8 from last hour" },
    { title: "Failed Logins", value: "23", change: "-5 from yesterday" },
    { title: "API Keys", value: "2,847", change: "+12 this week" },
    { title: "Security Score", value: "98.2%", change: "+0.3% this week" },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Security & Authentication</h1>
          <p className="text-muted-foreground">Manage authentication settings and monitor security</p>
        </div>
        <Button className="gap-2">
          <Plus className="w-4 h-4" />
          Create API Key
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

      {/* Security Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Security Settings</CardTitle>
          <CardDescription>Configure authentication and security policies</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="authentication" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="authentication">Authentication</TabsTrigger>
              <TabsTrigger value="policies">Policies</TabsTrigger>
              <TabsTrigger value="monitoring">Monitoring</TabsTrigger>
              <TabsTrigger value="encryption">Encryption</TabsTrigger>
            </TabsList>
            <TabsContent value="authentication" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Supabase Authentication</CardTitle>
                    <CardDescription>Primary authentication provider</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>Status</span>
                      <Badge variant="default">Active</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Users</span>
                      <span className="text-sm text-muted-foreground">1,247</span>
                    </div>
                    <Button variant="outline" size="sm" className="w-full">
                      <Settings className="w-4 h-4 mr-2" />
                      Configure
                    </Button>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Multi-Factor Authentication</CardTitle>
                    <CardDescription>Additional security layer</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>Enabled Users</span>
                      <span className="text-sm text-muted-foreground">234 (18.8%)</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Required for Admin</span>
                      <Badge variant="secondary">Enabled</Badge>
                    </div>
                    <Button variant="outline" size="sm" className="w-full">
                      <Shield className="w-4 h-4 mr-2" />
                      Manage MFA
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            
            <TabsContent value="policies" className="space-y-4">
              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Password Policy</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>Minimum Length</span>
                      <span className="text-sm text-muted-foreground">8 characters</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Require Uppercase</span>
                      <Badge variant="default">Required</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Require Numbers</span>
                      <Badge variant="default">Required</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Require Symbols</span>
                      <Badge variant="secondary">Optional</Badge>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Session Policy</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>Session Timeout</span>
                      <span className="text-sm text-muted-foreground">24 hours</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Concurrent Sessions</span>
                      <span className="text-sm text-muted-foreground">5 per user</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Force Logout on IP Change</span>
                      <Badge variant="destructive">Disabled</Badge>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            
            <TabsContent value="monitoring" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Failed Login Monitoring</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>Max Attempts</span>
                      <span className="text-sm text-muted-foreground">5 per hour</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Account Lockout</span>
                      <Badge variant="default">15 minutes</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Notifications</span>
                      <Badge variant="default">Enabled</Badge>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Audit Logging</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>Authentication Events</span>
                      <Badge variant="default">Enabled</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>API Access Logs</span>
                      <Badge variant="default">Enabled</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Retention Period</span>
                      <span className="text-sm text-muted-foreground">90 days</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            
            <TabsContent value="encryption" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Data Encryption</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>Secrets Encryption</span>
                      <Badge variant="default">AES-256</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Database Encryption</span>
                      <Badge variant="default">Enabled</Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Transport Security</span>
                      <Badge variant="default">TLS 1.3</Badge>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Key Management</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>Master Key Rotation</span>
                      <span className="text-sm text-muted-foreground">90 days</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Salt Generation</span>
                      <Badge variant="default">Per Secret</Badge>
                    </div>
                    <Button variant="outline" size="sm" className="w-full">
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Rotate Keys
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* API Keys Management */}
      <Card>
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
          <CardDescription>Manage API keys and access tokens</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Permissions</TableHead>
                <TableHead>Last Used</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {apiKeys.map((apiKey) => (
                <TableRow key={apiKey.id}>
                  <TableCell className="font-medium">{apiKey.name}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {apiKey.permissions.map((permission) => (
                        <Badge key={permission} variant="outline" className="text-xs">
                          {permission}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>{apiKey.lastUsed}</TableCell>
                  <TableCell>{apiKey.expires}</TableCell>
                  <TableCell>
                    <Badge variant={apiKey.status === "active" ? "default" : "destructive"}>
                      {apiKey.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex gap-2 justify-end">
                      <Button variant="ghost" size="sm">
                        <Eye className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        <RefreshCw className="w-4 h-4" />
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

      {/* Security Events */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Security Events</CardTitle>
          <CardDescription>Monitor authentication and security events</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Event</TableHead>
                <TableHead>User</TableHead>
                <TableHead>IP Address</TableHead>
                <TableHead>Time</TableHead>
                <TableHead>Severity</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {securityEvents.map((event) => (
                <TableRow key={event.id}>
                  <TableCell className="font-medium">{event.event}</TableCell>
                  <TableCell>{event.user}</TableCell>
                  <TableCell className="font-mono text-sm">{event.ip}</TableCell>
                  <TableCell>{event.time}</TableCell>
                  <TableCell>
                    <Badge variant={
                      event.severity === "high" ? "destructive" :
                      event.severity === "medium" ? "secondary" : "outline"
                    }>
                      {event.severity}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
} 