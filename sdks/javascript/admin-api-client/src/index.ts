/**
 * ProtoBox Admin API Client
 *
 * Auto-generated TypeScript client for the ProtoBox Admin API
 * Generated from OpenAPI specification
 */

// Export all generated types and clients
export * from './generated';

// Create a convenience function for initializing the client
import { client } from './generated/client.gen';

export interface AdminApiClientConfig {
  baseUrl?: string;
  headers?: Record<string, string>;
}

/**
 * Initialize the Admin API client with configuration
 *
 * @example
 * ```typescript
 * import { initializeClient } from '@protobox/admin-api-client';
 *
 * const apiClient = initializeClient({
 *   baseUrl: 'http://localhost:8090',
 *   headers: {
 *     'Authorization': 'Bearer YOUR_TOKEN'
 *   }
 * });
 * ```
 */
export function initializeClient(config: AdminApiClientConfig = {}) {
  const { baseUrl = 'http://localhost:8090', headers = {} } = config;

  client.setConfig({
    baseUrl,
    headers,
  });

  return client;
}

// Export the client instance
export { client as adminApiClient } from './generated/client.gen';
