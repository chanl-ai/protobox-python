# ProtoBox Admin API Client

TypeScript/JavaScript client for the ProtoBox Admin API, auto-generated from OpenAPI specification.

## Installation

```bash
npm install @protobox/admin-api-client
# or
pnpm add @protobox/admin-api-client
```

## Usage

```typescript
import { initializeClient } from '@protobox/admin-api-client';

const client = initializeClient({
  baseUrl: 'http://localhost:8090',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
});

// Get workspace tools
const tools = await client.getTools({ workspaceId: 'workspace_id' });

// Execute a tool
const result = await client.executeTool({
  workspaceId: 'workspace_id',
  toolId: 'tool_id',
  body: {
    input: 'params'
  }
});
```

## Development

### Generate Client from OpenAPI Spec

```bash
# Generate from localhost admin API
npm run generate

# Generate from custom URL
ADMIN_API_URL=http://localhost:8090 npm run generate
```

### Build

```bash
npm run build
```

### Regenerate Everything

```bash
npm run regenerate
```

## Structure

```
admin-api-client/
├── src/
│   ├── generated/      # Auto-generated from OpenAPI spec
│   └── index.ts        # Main exports
├── dist/               # Compiled output
├── scripts/
│   └── generate.js     # OpenAPI client generator
└── package.json
```

## Generated Files

The `src/generated/` directory contains:
- Type definitions for all API models
- Service classes for each API endpoint group
- Request/response types

**Do not edit generated files manually** - they will be overwritten on regeneration.

## License

MIT
