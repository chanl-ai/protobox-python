# Workers

Two Cloudflare Workers that the API calls to do work it should not do in its own process.

| Worker | What it does | API setting |
|---|---|---|
| `rest-executor` | Makes the outbound HTTP request for a REST tool and returns the response | `REST_EXECUTOR_WORKER_URL`, `REST_EXECUTOR_WORKER_TOKEN` |
| `code-executor-dispatcher` | Runs a code tool's worker from a Workers for Platforms dispatch namespace | `CLOUDFLARE_DISPATCHER_URL`, `CODE_EXECUTOR_WORKER_TOKEN` |

Both require a shared token. A worker without `WORKER_TOKEN` returns 503 for every request, and a
request without the matching `Authorization: Bearer` header gets 401.

## Deploy

```bash
cd workers/rest-executor
npm ci
TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')
echo "$TOKEN" | npx wrangler secret put WORKER_TOKEN
npx wrangler deploy
```

Put the deployed URL and the same token in the API's `.env`. The dispatcher also needs a dispatch
namespace binding named `DISPATCHER` in `wrangler.jsonc`.

## Test

```bash
npm ci && npx vitest run
```
