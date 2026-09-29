# API Client Migration Guide

## Status: ✅ Migration Complete

All components have been migrated from the old `apiClient` and named API exports (`actionsApi`, `secretsApi`, etc.) to the unified `protoboxClient` singleton.

## What Changed

### Removed: `skipAuth` Flag
- **Before**: `protoboxClient.request('/endpoint', { skipAuth: true })`
- **After**: Auth headers are always added automatically. When no token exists, `getAuthHeaders()` returns `{}`, so no Authorization header is sent.
- **Why**: Simplifies API - auth endpoints work without tokens, regular endpoints require tokens (backend validates).

### New: Auth Methods
All auth methods are now available on `protoboxClient`:
- `protoboxClient.exchangeToken(firebaseToken)` → `/auth/exchange`
- `protoboxClient.logout()` → `/auth/revoke`
- `protoboxClient.refreshToken()` → `/auth/refresh`
- `protoboxClient.validateToken()` → `/auth/validate`

### Migration Pattern

**Old Pattern (Deprecated):**
```typescript
import { actionsApi } from '@/lib/api/client'

const response = await actionsApi.list(workspaceId)
if (response.error) {
  // handle error
}
const actions = response.data
```

**New Pattern:**
```typescript
import { protoboxClient } from '@/lib/api/protobox-client'

const response = await protoboxClient.getActions(workspaceId)
if (response.error) {
  // handle error
}
const actions = response.data
```

**Or use React Query hooks (Recommended):**
```typescript
import { useActions } from '@/lib/api/hooks'

const { data: actions, loading, error } = useActions()
// No manual workspaceId passing needed!
```

## Deprecated APIs

All old API exports are deprecated and will be removed in v2.0:

- ❌ `apiClient` → Use `protoboxClient`
- ❌ `actionsApi` → Use `protoboxClient.getActions()`, `protoboxClient.createAction()`, etc.
- ❌ `secretsApi` → Use `protoboxClient.getSecrets()`, `protoboxClient.createSecret()`, etc.
- ❌ `workspaceApi` → Use `protoboxClient.getWorkspaces()`, `protoboxClient.createWorkspace()`, etc.
- ❌ `assistantsApi` → Use `protoboxClient.getAssistant()`, `protoboxClient.createAssistant()`, etc.
- ❌ `integrationsApi` → Use `protoboxClient.getAvailableIntegrations()`, `protoboxClient.getWorkspaceIntegrations()`, etc.
- ❌ `knowledgeApi` → Use `protoboxClient.listKnowledgeDocuments()`, `protoboxClient.uploadKnowledgeFile()`, etc.
- ❌ `executionsApi` → Use `protoboxClient.getExecutions()`, `protoboxClient.getExecution()`, etc.
- ❌ `statsApi` → Use `protoboxClient.getWorkspaceStats()`
- ❌ `userApi` → Use `protoboxClient.updateUserPreferences()`, etc.
- ❌ `authApi` → Use `protoboxClient.exchangeToken()`, `protoboxClient.logout()`, etc.

## Type Exports

Types are now exported from `client-types.ts`:
- `Action`, `Secret`, `Execution`, `Integration`, `IntegrationUIConfig`, `WorkspaceStats`, `WorkspaceListResponse`

**Import types from:**
```typescript
import type { Action, Secret, Execution } from '@/lib/api/client-types'
```

Types are also re-exported from `client.ts` for backward compatibility, but prefer importing from `client-types.ts`.

## Status: ✅ All Deprecated Code Removed

**All deprecated API code has been removed from `client.ts`**

The file now only contains type re-exports for backward compatibility:
- Types are re-exported from `client-types.ts`
- No deprecated API methods remain
- No deprecated classes or instances remain

**What was removed:**
- ❌ `ApiClient` class (not used anywhere)
- ❌ `apiClient` instance (not used anywhere)
- ❌ `workspaceApi`, `userApi`, `authApi`, `actionsApi`, `secretsApi`
- ❌ `executionsApi`, `assistantsApi`, `knowledgeApi`, `integrationsApi`, `statsApi`
- ❌ `api` convenience object

**Current state:**
- ✅ Types are in `client-types.ts` (preferred import location)
- ✅ Types re-exported from `client.ts` for backward compatibility only
- ✅ Zero deprecated code remaining
- ✅ All components use `protoboxClient` or React Query hooks

## Migration Checklist

- [x] Remove `skipAuth` flag from `protoboxClient`
- [x] Add auth methods to `protoboxClient`
- [x] Migrate all components to use `protoboxClient`
- [x] Remove all deprecated API methods and classes
- [x] Move types to separate file (`client-types.ts`)
- [x] Update all type imports (types imported from `@/lib/api/hooks` - correct!)
- [x] Add ESLint rule to ban imports from deprecated `client.ts`
- [x] Remove deprecated exports (completed!)

## WorkspaceProvider Removal (v2.0)

✅ **WorkspaceProvider has been removed**

The redundant React Context wrapper over `useAuthStore()` has been eliminated.

**Migration:**
- ❌ `import { useWorkspace } from '@/components/workspace-provider'`
- ✅ `import { useAuthStore } from '@/lib/auth/stores/auth.store'`

**Field Mapping:**
- `currentWorkspace` → `currentWorkspace` (direct)
- `workspaces` → `workspaces` (direct)
- `loading` → `workspaceLoading` (renamed in store)
- `error` → `error?.message` (store has Error object)
- `isReady` → Computed: `!workspaceLoading && !!currentWorkspace`
- `switchWorkspace(id)` → `selectWorkspace(id)`
- `refreshWorkspaces()` → `refreshWorkspaces()` (direct)

All components now use `useAuthStore()` directly as the single source of truth.

## Standalone API Classes (Optional Migration)

Some specialized API classes remain as wrappers around `protoboxClient`:

- `PromptsAPI` (prompts.ts) - Used 17 times
- `MCPOAuthAPI` (mcp-oauth.ts) - Used for OAuth client management
- `MCPTokensAPI` (mcp-tokens.ts) - Used for MCP token management
- `PartnerApi` (partners.ts) - Used for partner features
- `EmbedApiClient` (embed-client.ts) - Used for embed functionality

**Status:** These are thin wrappers that delegate to `protoboxClient` internally. They provide:
- Domain-specific interfaces
- Type safety for specialized features
- Convenience methods

**Recommendation:** Can migrate later if desired, but keeping them is acceptable since they're isolated and don't conflict with the main API architecture.

## Next Steps

1. **For New Code**: Always use `protoboxClient` or React Query hooks
2. **For Existing Code**: Old APIs still work but show deprecation warnings
3. **Type Imports**: Continue importing types from `client.ts` until v2.0
4. **Migration**: Gradually migrate any remaining internal code

## Questions?

- See `MIGRATION_GUIDE.md` for React Query hooks migration
- See `protobox-client.ts` for available methods
- All deprecated APIs delegate to `protoboxClient` internally

