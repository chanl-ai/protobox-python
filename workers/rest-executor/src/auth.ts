/**
 * Shared-token check for calls from the platform backend.
 *
 * This worker performs outbound requests (or runs customer code) on the platform's
 * behalf. Without a token check, anyone who learns its URL can use it as an open proxy.
 * Set the token with `wrangler secret put WORKER_TOKEN` and give the backend the same
 * value in REST_EXECUTOR_WORKER_TOKEN / CODE_EXECUTOR_WORKER_TOKEN.
 */
export function unauthorized(request: Request, expected: string | undefined): Response | null {
	if (!expected) {
		return json({ error: "Worker is not configured: WORKER_TOKEN is unset" }, 503);
	}
	const header = request.headers.get("Authorization") || "";
	const presented = header.startsWith("Bearer ") ? header.slice(7) : "";
	if (!timingSafeEqual(presented, expected)) {
		return json({ error: "Unauthorized" }, 401);
	}
	return null;
}

function timingSafeEqual(a: string, b: string): boolean {
	const enc = new TextEncoder();
	const x = enc.encode(a);
	const y = enc.encode(b);
	let diff = x.length ^ y.length;
	for (let i = 0; i < Math.max(x.length, y.length); i++) {
		diff |= (x[i] ?? 0) ^ (y[i] ?? 0);
	}
	return diff === 0;
}

function json(body: unknown, status: number): Response {
	return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
