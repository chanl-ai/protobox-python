import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { BarChart, LineChart, TrendingUp, TrendingDown, Download, RefreshCw } from "lucide-react"

export default function AnalyticsPage() {
  const stats = [
    { title: "Total Executions", value: "12,847", change: "+12.5%", trend: "up" },
    { title: "Active Users", value: "2,341", change: "+5.2%", trend: "up" },
    { title: "Avg Response Time", value: "285ms", change: "-8.3%", trend: "down" },
    { title: "Success Rate", value: "98.2%", change: "+0.5%", trend: "up" },
  ]

  const actionMetrics = [
    { name: "REST API Calls", executions: 4521, success: 98.5, avgTime: "245ms" },
    { name: "Database Queries", executions: 3247, success: 99.1, avgTime: "156ms" },
    { name: "Code Execution", executions: 2189, success: 95.3, avgTime: "1.2s" },
    { name: "O3 Reasoning", executions: 1890, success: 97.8, avgTime: "3.4s" },
  ]

  const userActivity = [
    { user: "john.doe@example.com", actions: 234, lastActive: "2 minutes ago", role: "Admin" },
    { user: "jane.smith@example.com", actions: 189, lastActive: "15 minutes ago", role: "Developer" },
    { user: "bob.wilson@example.com", actions: 156, lastActive: "1 hour ago", role: "User" },
    { user: "alice.brown@example.com", actions: 143, lastActive: "2 hours ago", role: "Developer" },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Analytics & Reporting</h1>
          <p className="text-muted-foreground">Monitor performance, usage, and system insights</p>
        </div>
        <div className="flex gap-2">
          <Select>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="Last 7 days" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1d">Last 24 hours</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 3 months</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" className="gap-2">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
          <Button className="gap-2">
            <Download className="w-4 h-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              {stat.trend === "up" ? (
                <TrendingUp className="w-4 h-4 text-green-500" />
              ) : (
                <TrendingDown className="w-4 h-4 text-red-500" />
              )}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className={`text-xs ${stat.trend === "up" ? "text-green-500" : "text-red-500"}`}>
                {stat.change} from last period
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts and Analytics */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Usage Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Usage Trends</CardTitle>
            <CardDescription>Action executions over time</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center border-2 border-dashed rounded-lg">
              <div className="text-center">
                <LineChart className="w-12 h-12 mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Usage trend chart would go here</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Performance Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Performance Metrics</CardTitle>
            <CardDescription>Response time and success rates</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center border-2 border-dashed rounded-lg">
              <div className="text-center">
                <BarChart className="w-12 h-12 mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Performance chart would go here</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Analytics */}
      <Card>
        <CardHeader>
          <CardTitle>Detailed Analytics</CardTitle>
          <CardDescription>Deep dive into system metrics and usage patterns</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="actions" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="actions">Actions</TabsTrigger>
              <TabsTrigger value="users">Users</TabsTrigger>
              <TabsTrigger value="performance">Performance</TabsTrigger>
              <TabsTrigger value="errors">Errors</TabsTrigger>
            </TabsList>
            
            <TabsContent value="actions" className="space-y-4">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Action Performance</h3>
                <div className="space-y-3">
                  {actionMetrics.map((action, index) => (
                    <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium">{action.name}</h4>
                          <Badge variant="outline">{action.executions} executions</Badge>
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">Success Rate:</span>
                            <span className="ml-2 font-medium">{action.success}%</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Avg Time:</span>
                            <span className="ml-2 font-medium">{action.avgTime}</span>
                          </div>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full" 
                            style={{ width: `${action.success}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="users" className="space-y-4">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">User Activity</h3>
                <div className="space-y-3">
                  {userActivity.map((user, index) => (
                    <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-medium">
                          {user.user.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium">{user.user}</p>
                          <p className="text-sm text-muted-foreground">{user.actions} actions</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant="outline">{user.role}</Badge>
                        <p className="text-xs text-muted-foreground mt-1">{user.lastActive}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="performance" className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">CPU Usage</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">42%</div>
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ width: `42%` }}
                      ></div>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">Average over last hour</p>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Memory Usage</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">67%</div>
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ width: `67%` }}
                      ></div>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">8.2 GB / 12 GB</p>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Disk Usage</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">34%</div>
                    <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full" 
                        style={{ width: `34%` }}
                      ></div>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">68 GB / 200 GB</p>
                  </CardContent>
                </Card>
              </div>
              
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Database Performance</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm">Query Time (avg)</span>
                      <span className="text-sm font-medium">156ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Connections</span>
                      <span className="text-sm font-medium">23 / 100</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Cache Hit Rate</span>
                      <span className="text-sm font-medium">89.2%</span>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">API Performance</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-sm">Requests/min</span>
                      <span className="text-sm font-medium">1,247</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Response Time (p95)</span>
                      <span className="text-sm font-medium">425ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Error Rate</span>
                      <span className="text-sm font-medium">1.8%</span>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
            
            <TabsContent value="errors" className="space-y-4">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Error Analysis</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Error Types</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Timeout Errors</span>
                        <div className="flex items-center gap-2">
                          <Badge variant="destructive">47</Badge>
                          <span className="text-sm text-muted-foreground">65%</span>
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Authentication Errors</span>
                        <div className="flex items-center gap-2">
                          <Badge variant="destructive">15</Badge>
                          <span className="text-sm text-muted-foreground">21%</span>
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Validation Errors</span>
                        <div className="flex items-center gap-2">
                          <Badge variant="destructive">10</Badge>
                          <span className="text-sm text-muted-foreground">14%</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Error Rate Trends</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm">Today</span>
                          <span className="text-sm font-medium">1.8%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm">Yesterday</span>
                          <span className="text-sm font-medium">2.3%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm">Last Week</span>
                          <span className="text-sm font-medium">2.1%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm">Last Month</span>
                          <span className="text-sm font-medium">2.7%</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
} 