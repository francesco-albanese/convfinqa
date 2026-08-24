.PHONY: frontend-install frontend-dev frontend-test frontend-browser-integration

frontend-install: ## Install frontend deps (frozen lockfile)
	cd frontend && pnpm install --frozen-lockfile

frontend-dev: ## Run Vite dev server (http://localhost:5173)
	cd frontend && pnpm dev

frontend-test: ## Run frontend unit tests (vitest)
	cd frontend && pnpm test

frontend-browser-integration: ## Run local browser integration tests
	cd frontend && pnpm browser:integration
