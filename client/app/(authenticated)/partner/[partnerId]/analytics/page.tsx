"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/ui/page-header"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  Activity,
  Download,
  Filter,
  Calendar
} from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'

// Dummy data
const mockMetrics = {
  totalRequests: 125430,
  activeWorkspaces: 89,
  avgResponseTime: 142,
  errorRate: 0.23
}

const mockUsageData = [
  { name: 'Jan', requests: 4000, workspaces: 24 },
  { name: 'Feb', requests: 5300, workspaces: 31 },
  { name: 'Mar', requests: 6200, workspaces: 45 },
  { name: 'Apr', requests: 7800, workspaces: 52 },
  { name: 'May', requests: 8900, workspaces: 67 },
  { name: 'Jun', requests: 10200, workspaces: 89 }
]

const mockTopEndpoints = [
  { endpoint: '/integrations', requests: 45230, percentage: 36.1 },
  { endpoint: '/actions', requests: 32140, percentage: 25.6 },
  { endpoint: '/workspaces', requests: 28950, percentage: 23.1 },
  { endpoint: '/tenants', requests: 19110, percentage: 15.2 }
]

const mockResponseTimes = [
  { time: '00:00', response: 120 },
  { time: '04:00', response: 98 },
  { time: '08:00', response: 165 },
  { time: '12:00', response: 201 },
  { time: '16:00', response: 178 },
  { time: '20:00', response: 142 }
]

interface AnalyticsPageProps {
  params: Promise<{ partnerId: string }>
}

export default async function AnalyticsPage({ params }: AnalyticsPageProps) {
  const { partnerId } = await params;
  const actions = [
    <Button variant="outline" key="filter">
      <Filter className="w-4 h-4 mr-2" />
      Filter
    </Button>,
    <Button variant="outline" key="date">
      <Calendar className="w-4 h-4 mr-2" />
      Last 30 days
    </Button>,
    <Button key="export">
      <Download className="w-4 h-4 mr-2" />
      Export
    </Button>
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        subtitle="Monitor your API usage, performance metrics, and customer activity"
        actions={actions}
      />

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockMetrics.totalRequests.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+12.3%</span> from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Workspaces</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockMetrics.activeWorkspaces}</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">+18.2%</span> from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockMetrics.avgResponseTime}ms</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">-5.4%</span> from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockMetrics.errorRate}%</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600">-0.12%</span> from last month
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <Tabs defaultValue="usage" className="space-y-4">
        <TabsList>
          <TabsTrigger value="usage">Usage Trends</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="endpoints">Top Endpoints</TabsTrigger>
        </TabsList>

        <TabsContent value="usage" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>API Usage Over Time</CardTitle>
              <CardDescription>
                Monthly API requests and active workspace growth
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={mockUsageData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Line 
                      type="monotone" 
                      dataKey="requests" 
                      stroke="#8884d8" 
                      strokeWidth={2}
                      name="API Requests"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="workspaces" 
                      stroke="#82ca9d" 
                      strokeWidth={2}
                      name="Active Workspaces"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Response Time Trends</CardTitle>
              <CardDescription>
                Average API response times throughout the day
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={mockResponseTimes}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="response" fill="#8884d8" name="Response Time (ms)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="endpoints" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Top API Endpoints</CardTitle>
              <CardDescription>
                Most frequently used endpoints by request volume
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockTopEndpoints.map((endpoint, index) => (
                  <div key={endpoint.endpoint} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <Badge variant="outline">{index + 1}</Badge>
                      <div>
                        <p className="font-medium">{endpoint.endpoint}</p>
                        <p className="text-sm text-muted-foreground">
                          {endpoint.requests.toLocaleString()} requests
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">{endpoint.percentage}%</p>
                      <div className="w-24 bg-gray-200 rounded-full h-2 mt-1">
                        <div 
                          className="bg-blue-600 h-2 rounded-full" 
                          style={{ width: `${endpoint.percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}