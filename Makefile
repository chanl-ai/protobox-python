SHELL := /bin/bash
.DEFAULT_GOAL := help

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup: ## Create .env files with random keys and install dependencies
	@test -f .env || { cp .env.example .env; \
	  for k in JWT_SECRET MCP_SECRET_KEY DOCUMENT_PROCESSOR_API_KEY; do \
	    v=$$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))'); \
	    sed -i.bak "s|^$$k=.*|$$k=$$v|" .env; done; rm -f .env.bak; echo "Created .env"; }
	@test -f client/.env.local || { cp client/.env.local.example client/.env.local; echo "Created client/.env.local"; }
	cd server && uv sync
	cd client && pnpm install --frozen-lockfile --config.confirmModulesPurge=false

up: ## Start the full stack in Docker (API on :8090)
	docker compose up -d --build

down: ## Stop the stack
	docker compose down

logs: ## Follow API logs
	docker compose logs -f api

web: ## Run the dashboard on :3010 against the API on :8090
	cd client && pnpm dev

api-dev: ## Run the API with hot reload against the Docker services
	docker compose up -d mongodb redis firebase-emulator document-processor
	cd server && set -a && source ../.env && set +a && \
	  MONGODB_URL='mongodb://localhost:27847/mcp_server?directConnection=true' \
	  REDIS_URL=redis://localhost:6381 FIREBASE_AUTH_EMULATOR_HOST=localhost:9299 \
	  DOCUMENT_PROCESSOR_URL=http://localhost:8092 \
	  uv run uvicorn protobox.admin.main:app --reload --port 8090

test: ## Run the offline test suites (no services needed)
	cd server && uv run pytest tests/security tests/unit -q
	cd services/document-processor && uv run pytest tests -q
	cd workers/rest-executor && npm ci --silent && npx vitest run
	cd workers/code-executor-dispatcher && npm ci --silent && npx vitest run

test-integration: ## Run integration tests against a running stack (make up first)
	cd server && uv run pytest tests/integration -q -m "not polling"

.PHONY: help setup up down logs web api-dev test test-integration
