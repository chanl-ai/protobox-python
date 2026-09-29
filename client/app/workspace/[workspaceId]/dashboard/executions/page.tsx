import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Search, RefreshCw, Pause, Square, Eye, AlertCircle, CheckCircle, Clock, X, RotateCcw } from "lucide-react"

export default function ExecutionsPage() {
  // Mock data for executions
  const executions = [
    { 
      id: "exec_1", 
      actionName: "Weather API", 
      status: "completed", 
      duration: "1.2s", 
      startTime: "2024-01-20 10:30:15",
      endTime: "2024-01-20 10:30:16",
      userId: "user_123",
      retryCount: 0,
      inputSize: "0.2KB",
      outputSize: "1.5KB"
    },
    { 
      id: "exec_2", 
      actionName: "Database Query", 
      status: "running", 
      duration: "5.8s", 
      startTime: "2024-01-20 10:29:45",
      endTime: null,
      userId: "user_456",
      retryCount: 0,
      inputSize: "1.1KB",
      outputSize: null
    },
    { 
      id: "exec_3", 
      actionName: "Python Script", 
      status: "failed", 
      duration: "15.2s", 
      startTime: "2024-01-20 10:28:30",
      endTime: "2024-01-20 10:28:45",
      userId: "user_789",
      retryCount: 2,
      inputSize: "3.2KB",
      outputSize: null
    },
    { 
      id: "exec_4", 
      actionName: "OpenAI Assistant", 
      status: "pending", 
      duration: null, 
      startTime: null,
      endTime: null,
      userId: "user_123",
      retryCount: 0,
      inputSize: "0.8KB",
      outputSize: null
    },
  ]

  const stats = [
    { title: "Total Executions", value: "1,247", change: "+127 from yesterday" },
    { title: "Success Rate", value: "98.2%", change: "+0.5% from last week" },
    { title: "Avg Duration", value: "2.3s", change: "-0.2s from last week" },
    { title: "Active Now", value: "12", change: "Real-time" },
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed": return <CheckCircle className="w-4 h-4 text-green-500" />
      case "running": return <Clock className="w-4 h-4 text-blue-500" />
      case "failed": return <X className="w-4 h-4 text-red-500" />
      case "pending": return <AlertCircle className="w-4 h-4 text-yellow-500" />
      case "cancelled": return <Square className="w-4 h-4 text-gray-500" />
      default: return <Clock className="w-4 h-4 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "default"
      case "running": return "secondary"
      case "failed": return "destructive"
      case "pending": return "outline"
      case "cancelled": return "secondary"
      default: return "outline"
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Executions Monitor</h1>
          <p className="text-muted-foreground">Track and monitor action executions in real-time</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" size="sm">
            <Pause className="w-4 h-4 mr-2" />
            Pause All
          </Button>
        </div>
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

      {/* Real-time Status */}
      <Card>
        <CardHeader>
          <CardTitle>Real-time Status</CardTitle>
          <CardDescription>Current execution status across all actions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-sm">Completed: 1,205</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-500" />
              <span className="text-sm">Running: 12</span>
            </div>
            <div className="flex items-center gap-2">
              <X className="w-4 h-4 text-red-500" />
              <span className="text-sm">Failed: 23</span>
            </div>
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-yellow-500" />
              <span className="text-sm">Pending: 7</span>
            </div>
          </div>
          <div className="mt-4">
            <div className="flex justify-between text-sm mb-2">
              <span>System Load</span>
              <span>68%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full" 
                style={{ width: `68%` }}
              ></div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Executions Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Execution History</CardTitle>
              <CardDescription>Recent action executions with detailed information</CardDescription>
            </div>
            <div className="flex gap-2">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input placeholder="Search executions..." className="pl-9 w-64" />
              </div>
              <Select>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Execution ID</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Start Time</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Retries</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {executions.map((execution) => (
                <TableRow key={execution.id}>
                  <TableCell className="font-mono text-sm">{execution.id}</TableCell>
                  <TableCell className="font-medium">{execution.actionName}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(execution.status)}
                      <Badge variant={getStatusColor(execution.status) as any}>
                        {execution.status}
                      </Badge>
                    </div>
                  </TableCell>
                  <TableCell>{execution.duration || "—"}</TableCell>
                  <TableCell>{execution.startTime || "—"}</TableCell>
                  <TableCell>{execution.userId}</TableCell>
                  <TableCell>
                    {execution.retryCount > 0 && (
                      <Badge variant="outline">{execution.retryCount}</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex gap-2 justify-end">
                      <Button variant="ghost" size="sm">
                        <Eye className="w-4 h-4" />
                      </Button>
                      {execution.status === "failed" && (
                        <Button variant="ghost" size="sm">
                          <RotateCcw className="w-4 h-4" />
                        </Button>
                      )}
                      {execution.status === "running" && (
                        <Button variant="ghost" size="sm">
                          <Square className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Performance Analytics */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Analytics</CardTitle>
          <CardDescription>Execution performance metrics and trends</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="performance">Performance</TabsTrigger>
              <TabsTrigger value="errors">Error Analysis</TabsTrigger>
            </TabsList>
            <TabsContent value="overview" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Today's Executions</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">247</div>
                    <div className="text-sm text-muted-foreground">+23% from yesterday</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Peak Hour</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">10 AM</div>
                    <div className="text-sm text-muted-foreground">45 executions</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Most Used Action</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-lg font-bold">Weather API</div>
                    <div className="text-sm text-muted-foreground">142 executions</div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            <TabsContent value="performance" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Average Response Time</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">2.3s</div>
                    <div className="text-sm text-muted-foreground">-0.2s from last week</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">95th Percentile</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">8.7s</div>
                    <div className="text-sm text-muted-foreground">Within SLA</div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            <TabsContent value="errors" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Error Rate</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">1.8%</div>
                    <div className="text-sm text-muted-foreground">-0.5% from last week</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Most Common Error</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-lg font-bold">Timeout</div>
                    <div className="text-sm text-muted-foreground">12 occurrences</div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
} 