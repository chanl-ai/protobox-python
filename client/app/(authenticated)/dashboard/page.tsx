"use client"

import * as React from "react"
import { useAuth } from "@/lib/auth"
import { useAuthStore } from "@/lib/auth/stores/auth.store"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { 
  Activity, 
  Users, 
  Zap, 
  CheckCircle,
  Download, 
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  AlertCircle,
  MoreVertical,
  ExternalLink
} from "lucide-react"
import { useState } from "react"
import Link from "next/link"
import { ExecutionsChart } from "@/components/dashboard/executions-chart"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  Database, 
  Code2, 
  Brain, 
  Plug, 
  Globe,
  Server,
  Cpu,
  Sparkles
} from "lucide-react"
import { useDashboardData } from "@/hooks/use-analytics"

export default function DashboardPage() {
  const { user } = useAuth()
  const { currentWorkspace } = useAuthStore()
  const [timeRange, setTimeRange] = useState("7d")
  
  // Use cached hooks for better performance
  const { 
    stats: dashboardStats, 
    metrics: executionMetrics, 
    activity: recentActivity,
    loading: isLoading,
    refetch: handleRefresh
  // WorkspaceLoadingGuard guarantees currentWorkspace exists
  } = useDashboardData(currentWorkspace!.id, timeRange)

  // Map dashboard stats to display format
  const stats = dashboardStats ? [
    {
      title: "Total Executions",
      value: dashboardStats.total_executions?.toLocaleString() || "0",
      change: Math.abs(dashboardStats.execution_change || 0),
      trend: (dashboardStats.execution_change || 0) >= 0 ? "up" as const : "down" as const,
      icon: Activity,
      description: "vs last period"
    },
    {
      title: "Active Users",
      value: dashboardStats.active_users?.toLocaleString() || "0",
      change: Math.abs(dashboardStats.user_change || 0),
      trend: (dashboardStats.user_change || 0) >= 0 ? "up" as const : "down" as const,
      icon: Users,
      description: "unique users"
    },
    {
      title: "Avg Response Time",
      value: `${dashboardStats.avg_response_time || 0}ms`,
      change: Math.abs(dashboardStats.response_time_change || 0),
      trend: (dashboardStats.response_time_change || 0) <= 0 ? "up" as const : "down" as const, // Lower is better
      icon: Clock,
      description: "median time"
    },
    {
      title: "Success Rate",
      value: `${dashboardStats.success_rate || 0}%`,
      change: Math.abs(dashboardStats.success_rate_change || 0),
      trend: (dashboardStats.success_rate_change || 0) >= 0 ? "up" as const : "down" as const,
      icon: CheckCircle,
      description: "all executions"
    },
  ] : []

  const quickActions = [
    { title: "Create Action", href: "/dashboard/actions", icon: Zap },
    { title: "View Analytics", href: "/dashboard", icon: Activity },
    { title: "Settings", href: "/dashboard/settings", icon: AlertCircle },
  ]

  const actionTypeIcons = {
    api: Globe,
    database: Database,
    code: Code2,
    ai: Brain,
    integration: Plug,
    server: Server,
    compute: Cpu,
    ml: Sparkles,
  }

  // Format time ago string
  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    if (seconds < 60) return `${seconds}s ago`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  // Format duration
  const formatDuration = (seconds: number) => {
    if (seconds < 1) return `${Math.round(seconds * 1000)}ms`
    return `${seconds.toFixed(1)}s`
  }

  // Prepare chart data from execution metrics
  const chartData = executionMetrics?.executions_by_date || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back, {user?.displayName || user?.email?.split('@')[0] || 'User'}
          </p>
        </div>
        <div className="flex gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">Last 24 hours</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 3 months</SelectItem>
            </SelectContent>
          </Select>
          <Button 
            variant="outline" 
            className="gap-2"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button className="gap-2">
            <Download className="w-4 h-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Key Metrics with Trending Display */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {isLoading ? (
          // Loading skeleton
          Array.from({ length: 4 }).map((_, index) => (
            <Card key={index}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="h-4 w-24 bg-muted animate-pulse rounded" />
                <div className="h-4 w-4 bg-muted animate-pulse rounded" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-32 bg-muted animate-pulse rounded mb-2" />
                <div className="h-3 w-20 bg-muted animate-pulse rounded" />
              </CardContent>
            </Card>
          ))
        ) : (
          stats.map((stat, index) => {
          const Icon = stat.icon
          const isPositive = stat.trend === "up" ? stat.change > 0 : stat.change < 0
          
          return (
            <Card key={index}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <div className="flex items-center gap-2 mt-1">
                  <div className={`flex items-center text-xs font-medium ${
                    isPositive ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {isPositive ? (
                      <ArrowUpRight className="h-3 w-3" />
                    ) : (
                      <ArrowDownRight className="h-3 w-3" />
                    )}
                    {Math.abs(stat.change)}%
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {stat.description}
                  </span>
                </div>
              </CardContent>
            </Card>
          )
        })
        )}
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
        {/* Chart Area - Spans 4 columns */}
        <div className="lg:col-span-4">
          <ExecutionsChart data={chartData} />
        </div>

        {/* Recent Activity - Spans 3 columns */}
        <Card className="lg:col-span-3">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div>
              <CardTitle className="text-lg">Recent Activity</CardTitle>
              <CardDescription className="text-sm">Latest action executions</CardDescription>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/dashboard/executions">
                View all
                <ExternalLink className="ml-2 h-3 w-3" />
              </Link>
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[300px] px-6">
              {(!recentActivity || recentActivity.length === 0) ? (
                <div className="flex flex-col items-center justify-center h-[280px] text-muted-foreground">
                  <svg className="h-12 w-12 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-sm font-medium">No recent activity</p>
                  <p className="text-xs mt-1">Action executions will appear here</p>
                </div>
              ) : (
              <div className="space-y-2 pb-4">
                {recentActivity.map((item, index) => {
                  const Icon = actionTypeIcons[item.action_type as keyof typeof actionTypeIcons] || Globe
                  return (
                    <div key={index} className="p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-lg bg-muted">
                            <Icon className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                                item.status === 'success' ? 'bg-green-500' : 'bg-red-500'
                              }`} />
                              <p className="text-sm font-medium font-mono truncate">{item.action_name}()</p>
                            </div>
                            <div className="flex items-center gap-2 mt-0.5">
                              <p className="text-xs text-muted-foreground">{item.description}</p>
                              <span className="text-xs text-muted-foreground">•</span>
                              <p className="text-xs text-muted-foreground">{getTimeAgo(item.time)}</p>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge 
                            variant="secondary"
                            className="text-xs"
                          >
                            {formatDuration(item.duration)}
                          </Badge>
                          <Button 
                            variant="ghost" 
                            size="icon"
                            className="h-6 w-6"
                          >
                            <MoreVertical className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-3">
        {quickActions.map((action, index) => {
          const Icon = action.icon
          return (
            <Card key={index} className="hover:shadow-md transition-shadow cursor-pointer">
              <Link href={action.href}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0">
                  <CardTitle className="text-base">{action.title}</CardTitle>
                  <Icon className="h-5 w-5 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Click to {action.title.toLowerCase()}
                  </p>
                </CardContent>
              </Link>
            </Card>
          )
        })}
      </div>
    </div>
  )
}