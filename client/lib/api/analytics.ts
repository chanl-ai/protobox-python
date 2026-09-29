import { protoboxClient } from './protobox-client'

export interface DashboardStats {
  total_executions: number
  active_users: number
  avg_response_time: number
  success_rate: number
  execution_change: number
  user_change: number
  response_time_change: number
  success_rate_change: number
}

export interface ExecutionMetrics {
  total_executions: number
  total_errors: number
  success_rate: number
  avg_response_time: number
  executions_by_date: Array<{
    date: string
    executions: number
    errors: number
  }>
  errors_by_date: Array<{
    date: string
    errors: number
  }>
}

export interface RecentActivity {
  action_name: string
  action_type: string
  description: string
  status: string
  time: string
  duration: number
  execution_id: string
}

export interface TopAction {
  action_name: string
  action_type: string
  count: number
  avg_duration: number
  error_rate: number
}

class AnalyticsAPI {
  async getDashboardStats(workspaceId: string, timeRange: string = '7d'): Promise<DashboardStats> {
    const params = new URLSearchParams({ time_range: timeRange })
    
    const response = await protoboxClient.getDashboardStats(workspaceId, timeRange)
    return response.data
  }

  async getExecutionMetrics(workspaceId: string, timeRange: string = '7d'): Promise<ExecutionMetrics> {
    const params = new URLSearchParams({ time_range: timeRange })
    
    const response = await protoboxClient.getExecutionMetrics(workspaceId, timeRange)
    return response.data
  }

  async getRecentActivity(workspaceId: string, limit: number = 10): Promise<RecentActivity[]> {
    const params = new URLSearchParams({ limit: limit.toString() })
    
    const response = await protoboxClient.getRecentActivity(workspaceId, limit)
    return response.data
  }

  async getTopActions(workspaceId: string, timeRange: string = '7d', limit: number = 5): Promise<TopAction[]> {
    const params = new URLSearchParams({ 
      time_range: timeRange,
      limit: limit.toString()
    })
    
    const response = await protoboxClient.getTopActions(workspaceId, timeRange, limit)
    return response.data
  }
}

export const analyticsAPI = new AnalyticsAPI()