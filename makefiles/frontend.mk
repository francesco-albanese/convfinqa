.PHONY: frontend-install frontend-dev frontend-test frontend-e2e

frontend-install: ## Install frontend deps (frozen lockfile)
	cd frontend && pnpm install --frozen-lockfile

frontend-dev: ## Run Vite dev server (http://localhost:5173)
	cd frontend && pnpm dev

frontend-test: ## Run frontend unit tests (vitest)
	cd frontend && pnpm test

frontend-e2e: ## Run frontend end-to-end tests (playwright-bdd)
	cd frontend && pnpm e2e
