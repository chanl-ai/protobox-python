# Security

This repository is a reference implementation and is not actively maintained. Do not rely on it to
protect production data without your own review. The README's
[Known limitations](README.md#known-limitations) section lists weaknesses that are known and unfixed.

## Reporting a vulnerability

Open a [GitHub security advisory](https://github.com/chanl-ai/protobox-python/security/advisories/new)
for this repository. Please do not open a public issue for an unfixed vulnerability.

## Protections in place, each covered by a test

| Protection | Test |
|---|---|
| The server refuses to start when `JWT_SECRET` or `MCP_SECRET_KEY` is missing, shorter than 32 characters, or a value that has appeared in this code | `server/tests/security/test_required_secrets.py` |
| Decrypted secrets and the worker token are never written to logs | `server/tests/security/test_rest_executor_secrets.py` |
| The egress and code workers reject calls without the shared token, and refuse to run when no token is configured | `workers/*/test/index.spec.ts` |
| The document processor refuses requests when its API key is unset | `services/document-processor/tests/test_auth.py` |
| An OAuth authorization code is only issued to a member of the workspace it grants access to; dynamically registered clients are bound to the workspace chosen at consent | `server/tests/security/test_oauth_consent_membership.py` |
| Knowledge base routes require a workspace member, and processing tasks are only visible from their own workspace | `server/tests/security/test_knowledge_base_access.py` |
| CORS allows only origins you configure (`CORS_ALLOWED_ORIGINS`, `FRONTEND_URL`), plus localhost in development | `server/src/protobox/admin/cors_config.py` |

Run them with `make test`.
