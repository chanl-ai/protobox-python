import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Search, Download, RefreshCw, Eye, AlertTriangle, CheckCircle, XCircle, User, Activity, Database, Shield } from "lucide-react"

export default function AuditLogsPage() {
  const auditLogs = [
    {
      id: "log_001",
      timestamp: "2024-01-22 14:30:25",
      user: "john.doe@example.com",
      action: "Action Created",
      resource: "REST API Weather",
      details: "Created new REST API action for weather data",
      severity: "info",
      ip: "192.168.1.100",
      userAgent: "Mozilla/5.0 (Mac...",
      status: "success"
    },
    {
      id: "log_002",
      timestamp: "2024-01-22 14:28:15",
      user: "jane.smith@example.com",
      action: "Secret Updated",
      resource: "API_KEY_OPENAI",
      details: "Updated OpenAI API key in secrets management",
      severity: "warning",
      ip: "10.0.0.15",
      userAgent: "Mozilla/5.0 (Win...",
      status: "success"
    },
    {
      id: "log_003",
      timestamp: "2024-01-22 14:25:45",
      user: "system",
      action: "Authentication Failed",
      resource: "Login",
      details: "Failed login attempt from unknown IP",
      severity: "error",
      ip: "203.0.113.42",
      userAgent: "Mozilla/5.0 (Linux...",
      status: "failed"
    },
    {
      id: "log_004",
      timestamp: "2024-01-22 14:20:12",
      user: "bob.wilson@example.com",
      action: "Action Executed",
      resource: "Database Query",
      details: "Executed database query action for user analytics",
      severity: "info",
      ip: "172.16.0.5",
      userAgent: "Mozilla/5.0 (Mac...",
      status: "success"
    },
    {
      id: "log_005",
      timestamp: "2024-01-22 14:15:33",
      user: "alice.brown@example.com",
      action: "User Created",
      resource: "test.user@example.com",
      details: "Created new user account with developer role",
      severity: "info",
      ip: "192.168.1.200",
      userAgent: "Mozilla/5.0 (Win...",
      status: "success"
    },
  ]

  const stats = [
    { title: "Total Events", value: "24,847", change: "+247 today", icon: Activity },
    { title: "Security Events", value: "127", change: "+12 today", icon: Shield },
    { title: "Failed Actions", value: "43", change: "-8 from yesterday", icon: XCircle },
    { title: "Active Users", value: "2,341", change: "+5 new today", icon: User },
  ]

  const eventTypes = [
    { type: "Authentication", count: 1247, percentage: 35 },
    { type: "Actions", count: 987, percentage: 28 },
    { type: "Secrets", count: 654, percentage: 18 },
    { type: "Users", count: 432, percentage: 12 },
    { type: "System", count: 234, percentage: 7 },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Audit Logs</h1>
          <p className="text-muted-foreground">Monitor system activity and security events</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
          <Button className="gap-2">
            <Download className="w-4 h-4" />
            Export Logs
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => {
          const Icon = stat.icon
          return (
            <Card key={index}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                <Icon className="w-4 h-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">{stat.change}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Event Types Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Event Types Distribution</CardTitle>
          <CardDescription>Breakdown of audit events by category</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            {eventTypes.map((event, index) => (
              <div key={index} className="text-center">
                <div className="text-2xl font-bold">{event.count}</div>
                <div className="text-sm text-muted-foreground">{event.type}</div>
                <div className="text-xs text-muted-foreground">{event.percentage}%</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Audit Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Audit Log Entries</CardTitle>
          <CardDescription>Detailed system activity and security events</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="all" className="w-full">
            <TabsList className="grid w-full grid-cols-5">
              <TabsTrigger value="all">All Events</TabsTrigger>
              <TabsTrigger value="security">Security</TabsTrigger>
              <TabsTrigger value="actions">Actions</TabsTrigger>
              <TabsTrigger value="users">Users</TabsTrigger>
              <TabsTrigger value="system">System</TabsTrigger>
            </TabsList>
            
            <TabsContent value="all" className="space-y-4">
              {/* Filters */}
              <div className="flex gap-2 mb-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input placeholder="Search logs..." className="pl-9" />
                </div>
                <Select>
                  <SelectTrigger className="w-32">
                    <SelectValue placeholder="Severity" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Levels</SelectItem>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="warning">Warning</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                  </SelectContent>
                </Select>
                <Select>
                  <SelectTrigger className="w-32">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="success">Success</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                  </SelectContent>
                </Select>
                <Select>
                  <SelectTrigger className="w-32">
                    <SelectValue placeholder="Time" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1h">Last Hour</SelectItem>
                    <SelectItem value="24h">Last 24 Hours</SelectItem>
                    <SelectItem value="7d">Last 7 Days</SelectItem>
                    <SelectItem value="30d">Last 30 Days</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Logs Table */}
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Timestamp</TableHead>
                    <TableHead>User</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Resource</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>IP Address</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {auditLogs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="font-mono text-sm">{log.timestamp}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-medium">
                            {log.user === "system" ? "S" : log.user.charAt(0).toUpperCase()}
                          </div>
                          <span className="text-sm">{log.user}</span>
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">{log.action}</TableCell>
                      <TableCell>{log.resource}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          {log.status === "success" ? (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          ) : (
                            <XCircle className="w-4 h-4 text-red-500" />
                          )}
                          <Badge variant={log.status === "success" ? "default" : "destructive"}>
                            {log.status}
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={
                          log.severity === "error" ? "destructive" :
                          log.severity === "warning" ? "secondary" : "outline"
                        }>
                          {log.severity}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-sm">{log.ip}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm">
                          <Eye className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TabsContent>
            
            <TabsContent value="security" className="space-y-4">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Security Events</h3>
                  <Badge variant="destructive">3 Critical</Badge>
                </div>
                <div className="space-y-3">
                  {auditLogs.filter(log => log.severity === "error" || log.action.includes("Auth")).map((log) => (
                    <div key={log.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <AlertTriangle className="w-5 h-5 text-red-500" />
                        <div>
                          <p className="font-medium">{log.action}</p>
                          <p className="text-sm text-muted-foreground">{log.details}</p>
                          <p className="text-xs text-muted-foreground">
                            {log.timestamp} • {log.ip}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant="destructive">{log.severity}</Badge>
                        <p className="text-xs text-muted-foreground mt-1">{log.user}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="actions" className="space-y-4">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Action Events</h3>
                <div className="space-y-3">
                  {auditLogs.filter(log => log.action.includes("Action") || log.action.includes("Executed")).map((log) => (
                    <div key={log.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Activity className="w-5 h-5 text-blue-500" />
                        <div>
                          <p className="font-medium">{log.action}</p>
                          <p className="text-sm text-muted-foreground">{log.details}</p>
                          <p className="text-xs text-muted-foreground">
                            {log.timestamp} • {log.resource}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant="outline">{log.severity}</Badge>
                        <p className="text-xs text-muted-foreground mt-1">{log.user}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="users" className="space-y-4">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">User Management Events</h3>
                <div className="space-y-3">
                  {auditLogs.filter(log => log.action.includes("User") || log.action.includes("Created")).map((log) => (
                    <div key={log.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <User className="w-5 h-5 text-green-500" />
                        <div>
                          <p className="font-medium">{log.action}</p>
                          <p className="text-sm text-muted-foreground">{log.details}</p>
                          <p className="text-xs text-muted-foreground">
                            {log.timestamp} • {log.resource}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant="outline">{log.severity}</Badge>
                        <p className="text-xs text-muted-foreground mt-1">{log.user}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="system" className="space-y-4">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">System Events</h3>
                <div className="space-y-3">
                  {auditLogs.filter(log => log.user === "system").map((log) => (
                    <div key={log.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Database className="w-5 h-5 text-purple-500" />
                        <div>
                          <p className="font-medium">{log.action}</p>
                          <p className="text-sm text-muted-foreground">{log.details}</p>
                          <p className="text-xs text-muted-foreground">
                            {log.timestamp} • {log.ip}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant={log.severity === "error" ? "destructive" : "outline"}>
                          {log.severity}
                        </Badge>
                        <p className="text-xs text-muted-foreground mt-1">System</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
} 