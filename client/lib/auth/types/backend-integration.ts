// UserLib Backend Integration Types

export interface BackendIntegrationConfig {
  internalApiUrl: string
  internalApiKey: string
}

export interface InternalApiClient {
  // User operations
  getUser(userId: string): Promise<any>
  createUser(userData: any): Promise<any>
  updateUser(userId: string, updates: any): Promise<any>
  updateUserPreferences(userId: string, preferences: any): Promise<any>
  
  // Workspace operations
  createWorkspace(data: any): Promise<any>
  getWorkspace(workspaceId: string): Promise<any>
  getWorkspaces(userId: string): Promise<any[]>
  updateWorkspace(workspaceId: string, updates: any): Promise<any>
  addWorkspaceMember(workspaceId: string, userId: string, role: string): Promise<any>
  
  // Billing operations
  getBillingInfo(userId: string): Promise<any>
  createSubscription(userId: string, planId: string, paymentMethodId: string): Promise<any>
  updateSubscription(subscriptionId: string, updates: any): Promise<any>
  cancelSubscription(subscriptionId: string): Promise<any>
  updateUsage(userId: string, metric: string, quantity: number): Promise<any>
}