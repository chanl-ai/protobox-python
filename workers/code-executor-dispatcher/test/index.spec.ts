import { env, createExecutionContext, waitOnExecutionContext } from 'cloudflare:test';
import { describe, it, expect } from 'vitest';
import worker from '../src/index';

const IncomingRequest = Request<unknown, IncomingRequestCfProperties>;

async function call(headers: Record<string, string>) {
	const request = new IncomingRequest('https://worker.example/', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', ...headers },
		body: JSON.stringify({ target_url: 'https://example.com/', worker_name: 'x', dispatch_namespace: 'y' }),
	});
	const ctx = createExecutionContext();
	const response = await worker.fetch(request, env as any, ctx);
	await waitOnExecutionContext(ctx);
	return response;
}

describe('caller authentication', () => {
	it('rejects a request with no token', async () => {
		expect((await call({})).status).toBe(401);
	});

	it('rejects a request with the wrong token', async () => {
		expect((await call({ Authorization: 'Bearer wrong-token' })).status).toBe(401);
	});

	it('lets a request with the right token reach request validation', async () => {
		const request = new IncomingRequest('https://worker.example/', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', Authorization: 'Bearer test-worker-token' },
			body: '{}',
		});
		const ctx = createExecutionContext();
		const response = await worker.fetch(request, env as any, ctx);
		expect(response.status).toBe(400);
	});

	it('refuses to run when no token is configured', async () => {
		const request = new IncomingRequest('https://worker.example/', { method: 'POST', body: '{}' });
		const ctx = createExecutionContext();
		const response = await worker.fetch(request, { ...(env as any), WORKER_TOKEN: undefined }, ctx);
		expect(response.status).toBe(503);
	});
});
