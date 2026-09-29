# Docs

Design notes written while the project was being built. They explain intent and are useful for
understanding the code, but some describe plans that were never finished. When a note and the code
disagree, the code is correct.

| Doc | Status |
|---|---|
| [API_ENDPOINTS_REFERENCE.md](API_ENDPOINTS_REFERENCE.md) | Reference; the live list is at `/docs` on a running API |
| [AUTH_ARCHITECTURE.md](AUTH_ARCHITECTURE.md), [AUTH_CONFIGURATION.md](AUTH_CONFIGURATION.md) | Current for Firebase login and JWT exchange |
| [OAUTH_IMPLEMENTATION.md](OAUTH_IMPLEMENTATION.md) | Current, except that consent now binds each code to a workspace the user belongs to |
| [MCP_ARCHITECTURE.md](MCP_ARCHITECTURE.md) | Historical migration plan; the live MCP handler is `server/src/protobox/admin/routers/mcp_multitenant.py` |
| [PUBLIC_MCP_ENDPOINTS.md](PUBLIC_MCP_ENDPOINTS.md) | Current |
| [DOCUMENT_PROCESSOR.md](DOCUMENT_PROCESSOR.md) | Current, except that there is no fallback when the processor is down and OCR is not performed |
| [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md), [INTEGRATION_OAUTH_GUIDE.md](INTEGRATION_OAUTH_GUIDE.md) | Current for adding a third-party integration |
| [GOOGLE_OAUTH_SETUP.md](GOOGLE_OAUTH_SETUP.md), [GOOGLE_CALENDAR_OAUTH_SETUP.md](GOOGLE_CALENDAR_OAUTH_SETUP.md) | Current |
| [SDK_GENERATION_GUIDE.md](SDK_GENERATION_GUIDE.md) | Current |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Partly historical; `make test` in the root README is the supported path |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Current |
