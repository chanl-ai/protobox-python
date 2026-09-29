# ProtoboxClient Migration Guide

## Overview

The new ProtoboxClient architecture provides a unified API client with React Query integration, automatic workspace/token injection, and standardized hooks.

## Key Benefits

- **No manual workspaceId passing** - Automatically injected from context
- **Standardized state management** - `{ data, loading, error, refetch }` everywhere
- **Optimistic updates** - Instant UI feedback with automatic rollback
- **Request deduplication** - React Query handles caching automatically
- **Type safety** - Full TypeScript support

## Migration Steps

### 1. Replace Manual API Calls with Hooks

**Before:**
```typescript
const [actions, setActions] = useState([])
const [loading, setLoading] = useState(true)
const [error, setError] = useState(null)

useEffect(() => {
  const fetchActions = async () => {
    try {
      setLoading(true)
      const response = await actionsApi.list(workspaceId)
      if (response.error) {
        setError(response.error)
      } else {
        setActions(response.data || [])
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  fetchActions()
}, [workspaceId])
```

**After:**
```typescript
import { useActions } from '@/lib/api/hooks'

const { data: actions, loading, error } = useActions()
// That's it! No manual state management needed
```

### 2. Replace Mutations with Hook Mutations

**Before:**
```typescript
const handleCreate = async (data) => {
  try {
    setLoading(true)
    const response = await actionsApi.create(workspaceId, data)
    if (response.error) {
      toast.error(response.error)
    } else {
      toast.success('Action created!')
      // Manually refetch
      await refetchActions()
    }
  } catch (err) {
    toast.error(err.message)
  } finally {
    setLoading(false)
  }
}
```

**After:**
```typescript
import { useCreateAction } from '@/lib/api/hooks'

const createAction = useCreateAction()

const handleCreate = async (data) => {
  try {
    await createAction.mutateAsync(data)
    toast.success('Action created!')
    // Cache automatically updated, no manual refetch needed
  } catch (err) {
    toast.error(err.message)
  }
}
```

### 3. Use useProtobox for Multiple Resources

**Before:**
```typescript
const [actions, setActions] = useState([])
const [secrets, setSecrets] = useState([])
const [workspaces, setWorkspaces] = useState([])
// ... lots of useState and useEffect
```

**After:**
```typescript
import { useProtobox } from '@/lib/api/hooks'

const { actions, secrets, workspaces } = useProtobox()
// All resources with standardized { data, loading, error, refetch }
```

### 4. Replace useParams for Workspace ID

**Before:**
```typescript
const params = useParams()
const workspaceId = params.workspaceId as string
// Problem: URL workspaceId might not match current workspace context
```

**After:**
```typescript
import { useWorkspaceReady } from '@/hooks'

const { workspaceId, isReady } = useWorkspaceReady()
// workspaceId comes from current workspace context, not URL
// ProtoboxClient hooks automatically use this workspaceId
```

### 5. Use Error Boundaries

**Before:**
```typescript
try {
  const response = await actionsApi.list(workspaceId)
  // handle response
} catch (error) {
  // manual error handling everywhere
}
```

**After:**
```typescript
import { ApiErrorBoundary } from '@/components/api-error-boundary'

<ApiErrorBoundary>
  <YourComponent />
</ApiErrorBoundary>
// Errors automatically caught and displayed
```

## Available Hooks

### Resource Hooks

- `useWorkspaces()` - List all workspaces
- `useWorkspace(id)` - Get single workspace
- `useCreateWorkspace()` - Create workspace (with optimistic update)
- `useUpdateWorkspace()` - Update workspace (with optimistic update)
- `useDeleteWorkspace()` - Delete workspace

- `useActions(workspaceId?, filters?)` - List actions
- `useAction(workspaceId?, actionId)` - Get single action
- `useCreateAction()` - Create action (with optimistic update)
- `useUpdateAction()` - Update action (with optimistic update)
- `useDeleteAction()` - Delete action

- `useSecrets(workspaceId?, filters?)` - List secrets
- `useSecret(workspaceId?, secretId)` - Get single secret
- `useCreateSecret()` - Create secret (with optimistic update)
- `useUpdateSecret()` - Update secret (with optimistic update)
- `useDeleteSecret()` - Delete secret

### Main Hook

- `useProtobox()` - Access all resources at once

## Backward Compatibility

The old API methods (`actionsApi`, `workspaceApi`, etc.) still work but show deprecation warnings. They delegate to ProtoboxClient internally.

**Status**: ✅ All components have been migrated to use `protoboxClient` or React Query hooks.

**Migration Priority:**
1. ✅ New components - Use new hooks from the start
2. ✅ Frequently used components - Migrated
3. ✅ Less used components - Migrated

See `API_MIGRATION.md` for details on the `protoboxClient` migration.

## Common Patterns

### Conditional Rendering
```typescript
const { actions, loading, error } = useActions()

if (loading) return <LoadingSpinner />
if (error) return <ErrorMessage error={error} />
if (!actions.data) return <EmptyState />

return <ActionsList actions={actions.data} />
```

### Optimistic Updates
```typescript
const updateAction = useUpdateAction()

// Optimistic update happens automatically
// UI updates immediately, rolls back on error
await updateAction.mutateAsync({ actionId, data })
```

### Manual Refetch
```typescript
const { actions, refetch } = useActions()

// Refetch when needed
await refetch()
```

## Troubleshooting

### Workspace Not Ready
If you see "No workspace selected" errors:
- Ensure workspace is loaded: `useWorkspaceReady().isReady`
- Use `useWorkspaceReady()` hook to check readiness
- ProtoboxClient automatically validates workspace before API calls

### Cache Not Updating
- Mutations automatically invalidate related queries
- Use `queryClient.invalidateQueries()` for manual invalidation
- Check query keys match between queries and mutations

### Type Errors
- All hooks are fully typed
- Import types from hooks: `import type { Action } from '@/lib/api/hooks'`
- Use TypeScript's autocomplete for available properties

## Next Steps

1. Start using new hooks in new components
2. Migrate one resource type at a time (e.g., all actions pages)
3. Remove old API client usage after migration complete
4. Delete `compat.ts` after full migration

