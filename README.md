# Protobox (Python)

Protobox is a self-hostable, multi-tenant service that turns a team's APIs and documents into an
MCP server. You create a workspace, add tools (REST calls with encrypted secrets, imported from
OpenAPI or cURL), upload documents to a knowledge base, and hand the workspace's MCP URL to an AI
client such as Claude, ChatGPT or Cursor. The client signs in with OAuth 2.1 or an API token, lists
the workspace's tools and calls them.

It has three parts: a FastAPI server (API, MCP endpoint, OAuth authorization server), a Next.js
dashboard, and a document-processing service for PDF, DOCX and XLSX files.

**Status: reference implementation, not actively maintained.** It is published for people building
MCP platforms who want a working, readable example. Read [Known limitations](#known-limitations)
before running it anywhere public.

## Run it

You need Docker, Python 3.11+ with [uv](https://docs.astral.sh/uv/), Node.js 20+ with pnpm, and
make. No cloud accounts are needed: authentication runs on the Firebase Auth emulator.

```bash
git clone https://github.com/chanl-ai/protobox-python.git
cd protobox-python
make setup   # creates .env and client/.env.local with random keys, installs dependencies
make up      # MongoDB, Redis, Firebase Auth emulator, document processor, API on :8090
make web     # dashboard on http://localhost:3010
```

Check the API with `curl http://localhost:8090/health`. Open <http://localhost:3010> and sign up
with any email and password; the emulator accepts anything.

Optional settings in `.env`:

| Variable | Needed for |
|---|---|
| `OPENAI_API_KEY` | The knowledge base. Without it, knowledge base routes return 503 and the MCP search tool returns no results. |
| `AWS_*` (any S3-compatible store) | Uploading files to the knowledge base. Text and URL sources work without it. |
| `REST_EXECUTOR_WORKER_URL`, `REST_EXECUTOR_WORKER_TOKEN` | Running REST tools. Outbound calls go through the egress worker in [`workers/`](workers/README.md). |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google integrations. |

`make help` lists every target. `make api-dev` runs the API with hot reload instead of in Docker.

## Common tasks

### 1. Add a tool

In the dashboard, create an action by hand or import an OpenAPI spec or a cURL command. Reference
secrets from headers as `${secret:name}` or `${secret:name.field}`, and create them on the Secrets
page. Values are encrypted with AES-256-GCM and never returned by the API.

### 2. Connect an AI client

Create an MCP token for the workspace. The MCP endpoint is:

```
GET http://localhost:8090/mcp/<workspace_id>/sse
Authorization: Bearer pb_mcp_...
```

Clients that support OAuth can use `http://localhost:8090/mcp` instead. They register themselves,
send you to the dashboard's consent screen, and receive a token for the workspace you choose there.

### 3. Search your documents from the AI client

Add a file, a URL or text to the knowledge base. Once processing finishes, the workspace's MCP
server exposes a `search_knowledge_base` tool with semantic, keyword and hybrid modes.

## Tests

`make test` runs the offline suites: security regression tests, unit tests, the document processor
and both egress workers. `make test-integration` runs against a live stack started with `make up`.
Some older tests under `server/tests/admin` fail against the current models and are not part of
`make test`.

## Known limitations

These are known and not fixed. Each is a reason not to expose an instance to the internet without
further work.

- **MCP transport.** Only the SSE transport works. `POST /mcp/{workspace_id}` (Streamable HTTP)
  returns placeholder tools and cannot run them. SSE sessions live in process memory, so running more
  than one API instance needs sticky routing. The SSE message URL carries the token as a query
  parameter, which proxies may log.
- **Tool types.** REST tools work. Code tools run on Cloudflare Workers for Platforms and have
  error-handling bugs. `O3` and `DATABASE` types are not implemented, and one such action in a
  workspace makes the MCP tool list fall back to the knowledge base tool only.
- **History.** Tool calls made over MCP are not recorded in execution history.
- **Knowledge base.** Processing runs as an in-process background task with no retries. Vector search
  fetches global top results and then filters by workspace, so recall drops as tenants grow. OCR is
  accepted as an option but not performed. There are no source connectors (SharePoint, GitHub and so
  on) and no per-document permissions.
- **Authorization.** Workspace access is checked in three places with slightly different rules
  (`auth/workspace_dependencies.py`, `middleware/team_auth.py`, `routers/workspace.py`), and team
  membership is stored both on the workspace document and in `workspace_members`.
- **Dashboard dependencies.** The playground chat uses AI SDK v4, which has two low-severity
  advisories (a file-type check bypass and a resource-consumption issue). Both are fixed only in
  v5, which changes the chat hooks this page is built on.
- **Unused code.** `server/src/protobox/{actions,resources,context,tools}` and parts of `protocol/`
  are stubs used only by the alternative `protobox-server` CLI bootstrap, not by the API.

## Layout

| Path | What it is |
|---|---|
| `server/` | FastAPI app: admin API under `/admin/api/v1`, MCP endpoints under `/mcp`, OAuth 2.1 authorization server |
| `client/` | Next.js dashboard (shadcn/ui) |
| `services/document-processor/` | PDF, DOCX and XLSX parsing service, called by the server with an API key |
| `workers/` | Cloudflare Workers that make outbound HTTP calls and run code tools |
| `sdks/javascript/` | Generated TypeScript client for the admin API |
| `examples/` | MCP client examples |
| `docs/` | Design notes; see [docs/README.md](docs/README.md) |

## License

MIT. See [LICENSE](LICENSE). To report a vulnerability, see [SECURITY.md](SECURITY.md).
