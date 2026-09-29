import { AuditLog, AuditLogFilter, AuditLogStats } from '@/lib/types/audit';
import { protoboxClient } from './protobox-client';

// Audit logs API following the same pattern as other APIs
export const auditApi = {
  /**
   * Get audit logs with optional filtering
   */
  getLogs: (workspaceId: string, filter?: AuditLogFilter) => {
    const params: any = {};
    
    if (filter?.user_id) params.user_id = filter.user_id;
    if (filter?.resource_type) params.resource_type = filter.resource_type;
    if (filter?.action) params.action = filter.action;
    if (filter?.start_date) params.start_date = filter.start_date;
    if (filter?.end_date) params.end_date = filter.end_date;
    if (filter?.limit) params.limit = filter.limit;
    if (filter?.offset) params.offset = filter.offset;

    const queryString = new URLSearchParams(params).toString();
    return protoboxClient.request<{ logs: AuditLog[]; total: number }>(
      `/workspaces/${workspaceId}/audit-logs${queryString ? `?${queryString}` : ''}`
    );
  },

  /**
   * Get audit log by ID
   */
  getLogById: (workspaceId: string, logId: string) =>
    protoboxClient.request<AuditLog>(`/workspaces/${workspaceId}/audit-logs/${logId}`),

  /**
   * Get audit history for a specific resource
   */
  getResourceHistory: (
    workspaceId: string,
    resourceType: string,
    resourceId: string,
    limit: number = 50
  ) =>
    protoboxClient.request<AuditLog[]>(
      `/workspaces/${workspaceId}/audit-logs/resource/${resourceType}/${resourceId}?limit=${limit}`
    ),

  /**
   * Get user activity logs
   */
  getUserActivity: (workspaceId: string, userId: string, limit: number = 100) =>
    protoboxClient.request<AuditLog[]>(
      `/workspaces/${workspaceId}/audit-logs/users/${userId}?limit=${limit}`
    ),

  /**
   * Get audit log statistics
   */
  getStatistics: (workspaceId: string, startDate?: string, endDate?: string) => {
    const params: any = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const queryString = new URLSearchParams(params).toString();
    return protoboxClient.request<AuditLogStats>(
      `/workspaces/${workspaceId}/audit-logs/statistics${queryString ? `?${queryString}` : ''}`
    );
  },
};