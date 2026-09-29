/**
 * Available OAuth scopes for MCP clients
 */
export const AVAILABLE_OAUTH_SCOPES = [
  { value: "mcp:read", label: "Read", description: "Access to read MCP resources and tool information" },
  { value: "mcp:execute", label: "Execute", description: "Permission to execute MCP tools and actions" },
  { value: "mcp:write", label: "Write", description: "Access to modify MCP resources and configurations" },
] as const

export type OAuthScopeValue = typeof AVAILABLE_OAUTH_SCOPES[number]['value']
