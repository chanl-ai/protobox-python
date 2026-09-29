import { unauthorized } from "./auth";
/**
 * Code Executor Dispatcher
 * Dispatches requests to the code executor worker, which executes customer's code in a safe 
 * environment (cloudflare "workers for platforms" service).
 * 
 * - Run `npm run dev` in your terminal to start a development server
 * - Open a browser tab at http://localhost:8787/ to see your worker in action
 * - Run `npm run deploy` to publish your worker
 *
 * Bind resources to your worker in `wrangler.jsonc`. After adding bindings, a type definition for the
 * `Env` object can be regenerated with `npm run cf-typegen`.
 *
 * Learn more at https://developers.cloudflare.com/workers/
 */


interface DispatcherRequest {
	worker_name: string;
	dispatch_namespace: string;
	language?: string;
	entry_point?: string;
	timeout?: number;
	memory_limit_mb?: number;
	dependencies?: string[];
	allowed_imports?: string[];
	allow_network?: boolean;
	allow_file_ops?: boolean;
	input_data?: Record<string, any>;
}

export default {
	async fetch(request, env, ctx): Promise<Response> {
		const denied = unauthorized(request, (env as any).WORKER_TOKEN);
		if (denied) return denied;

		try {
			// Clone the request to preserve the original body
			const requestClone = request.clone();
			
			// Parse the request body to get worker information
			const requestBody = await request.json() as DispatcherRequest;
			const workerName = requestBody.worker_name;
			const dispatchNamespace = requestBody.dispatch_namespace;
			
			if (!workerName) {
				return new Response(
					JSON.stringify({
						success: false,
						error: "Missing worker_name in request body"
					}),
					{
						status: 400,
						headers: { "Content-Type": "application/json" }
					}
				);
			}
			
			// Get the customer worker from the dispatch namespace
			// The DISPATCHER binding is already configured to point to the correct namespace
			const worker = env.DISPATCHER.get(workerName);
			
			if (!worker) {
				return new Response(
					JSON.stringify({
						success: false,
						error: `Worker '${workerName}' not found in dispatch namespace`
					}),
					{
						status: 404,
						headers: { "Content-Type": "application/json" }
					}
				);
			}
			
			// Create a new request with the original body for the customer worker
			const customerRequest = new Request(request.url, {
				method: request.method,
				headers: request.headers,
				body: await requestClone.text(),
			});
			
			// Forward the request to the customer worker
			const customerResponse = await worker.fetch(customerRequest);
			
			// Return the response with proper headers
			return new Response(customerResponse.body, {
				status: customerResponse.status,
				statusText: customerResponse.statusText,
				headers: customerResponse.headers
			});
			
		} catch (error) {
			// Handle JSON parsing errors or other issues
			return new Response(
				JSON.stringify({
					success: false,
					error: `Dispatcher error: ${error instanceof Error ? error.message : 'Unknown error'}`
				}),
				{
					status: 500,
					headers: { "Content-Type": "application/json" }
				}
			);
		}
	},
} satisfies ExportedHandler<Env>;
