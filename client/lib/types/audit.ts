// Audit log types that match the backend schema

export enum AuditAction {
  CREATE = "CREATE",
  UPDATE = "UPDATE",
  DELETE = "DELETE",
  READ = "READ",
  LOGIN = "LOGIN",
  LOGOUT = "LOGOUT",
  INVITE = "INVITE",
  REVOKE = "REVOKE",
  EXECUTE = "EXECUTE"
}

export interface AuditLog {
  id: string;
  timestamp: string;
  user_id: string;
  user_email?: string;  // Optional - can be populated later from user table
  user_name?: string;   // Optional - populated from user table
  workspace_id: string;
  action: AuditAction | string;  // Allow string for flexibility
  resource_type: "user" | "workspace" | "action" | "secret" | "execution" | "audit_log" | string;
  resource_id?: string;  // Make optional as some audit logs might not have resource_id
  ip_address?: string;   // Optional - IP address of the user
  user_agent?: string;   // Optional - User agent string
  status?: "success" | "failure" | "warning";  // Optional - status of the action
  details?: Record<string, any>;  // Optional - additional details
  changes?: {
    before: any;
    after: any;
  };
  metadata?: Record<string, any>;
}

export interface AuditLogFilter {
  workspace_id?: string;
  user_id?: string;
  resource_type?: string;
  action?: AuditAction;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

export interface AuditLogStats {
  by_resource: Record<string, {
    total: number;
    actions: Record<string, number>;
  }>;
  total_actions: number;
  unique_users: number;
}