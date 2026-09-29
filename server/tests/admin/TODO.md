# Admin Tests TODO

This checklist tracks the improvements and coverage gaps for the `tests/admin` suite.

## 1. Test Discovery & Imports
+ [x] Fix import paths: change `from src.protobox.admin...` → `from protobox.admin...`
+ [x] Verify `tests/admin` modules discoverable (add/update `conftest.py` or PYTHONPATH as needed)

## 2. Coverage Gaps
The following modules in `src/protobox/admin` currently have low or no test coverage. Please add focused unit tests for:

- **Actions**
  - [ ] `actions/rest_executor.py`

- **Authentication**
  - [ ] `auth/api_key_auth.py`
  - [ ] `auth/dependencies.py`
  - [ ] `auth/routes.py`
  - [ ] `auth/supabase_auth.py`

- **Database**
  - [ ] `database/connection.py`
  - [ ] `database/repositories/action_repository.py`
  - [ ] `database/repositories/execution_repository.py`
  - [ ] `database/repositories/secret_repository.py`

- **Health & Main**
  - [ ] `health.py`
  - [ ] `main.py`

- **MCP / Multitenant**
  - [ ] `mcp/fastmcp_simple.py`
  - [ ] `mcp/multitenant/core.py`
  - [ ] `mcp/multitenant/hooks.py`
  - [ ] `mcp/multitenant/routing.py`
  - [ ] `mcp/multitenant/tool_registry.py`

- **Middleware**
  - [ ] `middleware/workspace_auth.py`

- **Models**
  - [x] `models/action.py`
  - [ ] `models/assistant.py`
  - [ ] `models/chat.py`
  - [x] `models/execution.py`
  - [ ] `models/secret.py`
  - [ ] `models/workspace.py`

- **Router & Sub-routers**
  - [ ] `router.py`
  - [ ] `routers/actions.py`
  - [ ] `routers/assistants.py`
  - [ ] `routers/chat.py`
  - [ ] `routers/mcp_fastmcp_simple.py`
  - [ ] `routers/mcp_multitenant.py`
  - [ ] `routers/mcp_sse.py`
  - [ ] `routers/workspace.py`

- **Secrets**
  - [ ] `secrets/encryption.py`
  - [ ] `secrets/types.py`
  - [ ] `secrets/validator.py`

- **Services**
  - [ ] `services/action_service.py`
  - [ ] `services/assistant_service.py`
  - [ ] `services/chat_service.py`
  - [ ] `services/secret_service.py`
  - [ ] `services/workspace_service.py`

## 3. Quality & Best Practices Audit
- [ ] Audit a representative test file for:
  - Clear naming & docstrings
  - AAA (Arrange, Act, Assert) structure
  - DRY fixtures / helpers
  - Behavioral (not implementation) assertions
  - No flakiness (timing/order independent)

## 4. Continuous Improvement
- [ ] After adding/refactoring tests, re-run coverage and update this checklist.
- [ ] Keep this file up-to-date as new admin features arrive.
