import { unauthorized } from "./auth";
/**
 * REST Executor Worker
 * 
 * Handles HTTP requests by forwarding them to target APIs.
 * 
 * Expected request body format:
 * {
 *     "target_url": "https://api.example.com/endpoint",
 *     "method": "GET",
 *     "headers": {"Authorization": "Bearer token"},
 *     "timeout": 30,
 *     "allow_redirects": true,
 *     "verify_ssl": true,
 *     "json": {...},  // Optional JSON body
 *     "data": "...",  // Optional form data
 *     "params": {...}  // Optional query parameters
 * }
 */

interface RequestPayload {
	target_url: string;
	method?: string;
	headers?: Record<string, string>;
	timeout?: number;
	allow_redirects?: boolean;
	verify_ssl?: boolean;
	json?: any;
	data?: string;
	params?: Record<string, string>;
}

interface ResponseData {
	status_code: number;
	headers: Record<string, string>;
	body: any;
	url: string;
	reason: string;
}

interface ErrorResponse {
	error: string;
	error_type: string;
}

export default {
	async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
		const denied = unauthorized(request, (env as any).WORKER_TOKEN);
		if (denied) return denied;

		try {
			// Only handle POST requests with JSON payload
			if (request.method !== "POST") {
				return new Response(
					JSON.stringify({ error: "Only POST requests are supported" }),
					{
						status: 405,
						headers: { "Content-Type": "application/json" }
					}
				);
			}

			// Parse the request payload
			let payload: RequestPayload;
			try {
				payload = await request.json();
			} catch (e) {
				return new Response(
					JSON.stringify({ error: `Invalid JSON payload: ${e}` }),
					{
						status: 400,
						headers: { "Content-Type": "application/json" }
					}
				);
			}

			// Extract required fields
			const targetUrl = payload.target_url;
			const method = payload.method || "GET";

			if (!targetUrl) {
				return new Response(
					JSON.stringify({ error: "target_url is required" }),
					{
						status: 400,
						headers: { "Content-Type": "application/json" }
					}
				);
			}

			// Prepare the request to the target API
			const requestInit: RequestInit = {
				method: method,
				headers: payload.headers || {},
				redirect: payload.allow_redirects !== false ? "follow" : "manual",
			};

			// Add body data if present
			if (payload.json !== undefined) {
				requestInit.body = JSON.stringify(payload.json);
				requestInit.headers = {
					...requestInit.headers,
					"Content-Type": "application/json"
				};
			} else if (payload.data !== undefined) {
				requestInit.body = payload.data;
			}

			// Add query parameters if present
			let finalUrl = targetUrl;
			if (payload.params) {
				const url = new URL(targetUrl);
				Object.entries(payload.params).forEach(([key, value]) => {
					url.searchParams.append(key, value);
				});
				finalUrl = url.toString();
			}

			// Make the request to the target API
			const response = await fetch(finalUrl, requestInit);

			// Try to parse response body
			let body: any;
			try {
				const contentType = response.headers.get("content-type") || "";
				
				if (contentType.startsWith("application/json")) {
					try {
						body = await response.json();
					} catch {
						// If JSON parsing fails, fall back to text
						body = await response.text();
					}
				} else {
					body = await response.text();
				}
			} catch (e) {
				// Fallback: return raw content as base64 if we can't decode it
				const arrayBuffer = await response.arrayBuffer();
				const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
				body = {
					raw_content: base64,
					content_type: response.headers.get("content-type") || "unknown",
					decode_error: String(e)
				};
			}

			// Convert headers to plain object
			const responseHeaders: Record<string, string> = {};
			response.headers.forEach((value, key) => {
				responseHeaders[key] = value;
			});

			// Return the response in the expected format
			const responseData: ResponseData = {
				status_code: response.status,
				headers: responseHeaders,
				body: body,
				url: response.url,
				reason: response.statusText,
			};

			return new Response(
				JSON.stringify(responseData),
				{
					status: 200,
					headers: { "Content-Type": "application/json" }
				}
			);

		} catch (e) {
			// Return error response
			const errorResponse: ErrorResponse = {
				error: String(e),
				error_type: e instanceof Error ? e.constructor.name : "UnknownError",
			};

			return new Response(
				JSON.stringify(errorResponse),
				{
					status: 500,
					headers: { "Content-Type": "application/json" }
				}
			);
		}
	},
} satisfies ExportedHandler<Env>;
