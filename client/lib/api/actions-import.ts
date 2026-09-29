/**
 * API client for importing actions from OpenAPI specs and cURL commands
 */

import { protoboxClient } from './protobox-client'

// Types
export interface OpenAPIImportRequest {
  spec_url?: string
  spec_content?: string
  include_paths?: string[]
  exclude_paths?: string[]
  base_url_override?: string
}

export interface CurlImportRequest {
  curl_command: string
  name?: string
  description?: string
}

export interface ActionPreview {
  name: string
  description?: string
  method: string
  url: string
  variables: Array<{
    name: string
    type: string
    required: boolean
    description: string
    in?: string  // path, query, header, cookie, body
    example?: any
    schema?: Record<string, any>  // For complex types
  }>
  request_example?: {
    content_type: string
    body: any
  }
  response_examples?: Record<string, {
    description: string
    content_type: string
    body: any
  }>
  tags?: string[]
  security_schemes?: string[]
}

export interface ImportPreviewResponse {
  actions_count: number
  previews: ActionPreview[]
}

export interface ImportResult {
  created: string[]
  skipped: Array<{
    name: string
    reason: string
  }>
  summary: {
    parsed: number
    created: number
    skipped: number
  }
}

export class ActionsImportAPI {
  /**
   * Preview actions from an OpenAPI specification
   */
  static async previewOpenAPI(
    workspaceId: string,
    request: OpenAPIImportRequest
  ): Promise<ImportPreviewResponse> {
    const response = await protoboxClient.request(
      `/workspaces/${workspaceId}/actions/import/openapi/preview`,
      {
        method: 'POST',
        body: request,
      }
    )
    return response.data!
  }

  /**
   * Create actions from an OpenAPI specification
   */
  static async createFromOpenAPI(
    workspaceId: string,
    request: OpenAPIImportRequest
  ): Promise<ImportResult> {
    const response = await protoboxClient.request(
      `/workspaces/${workspaceId}/actions/import/openapi/create`,
      {
        method: 'POST',
        body: request,
      }
    )
    return response.data!
  }

  /**
   * Preview action from a cURL command
   */
  static async previewCurl(
    workspaceId: string,
    request: CurlImportRequest
  ): Promise<ImportPreviewResponse> {
    const response = await protoboxClient.request(
      `/workspaces/${workspaceId}/actions/import/curl/preview`,
      {
        method: 'POST',
        body: request,
      }
    )
    return response.data!
  }

  /**
   * Create action from a cURL command
   */
  static async createFromCurl(
    workspaceId: string,
    request: CurlImportRequest
  ): Promise<ImportResult> {
    const response = await protoboxClient.request(
      `/workspaces/${workspaceId}/actions/import/curl/create`,
      {
        method: 'POST',
        body: request,
      }
    )
    return response.data!
  }
}
