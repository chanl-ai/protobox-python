/**
 * Type re-exports for backward compatibility
 * 
 * All types are now defined in './client-types'.
 * This file exists only to maintain backward compatibility for existing imports.
 * 
 * For new code, import types directly from './client-types'.
 */

// Re-export all types from client-types.ts
export type {
  Integration,
  IntegrationUIConfig,
  WorkspaceListResponse,
  Action,
  Secret,
  Execution,
  WorkspaceStats,
} from './client-types'
