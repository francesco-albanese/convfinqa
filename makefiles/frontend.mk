.PHONY: frontend-install frontend-dev frontend-test frontend-browser-integration frontend-e2e-live-docker

frontend-install: ## Install frontend deps (frozen lockfile)
	cd frontend && pnpm install --frozen-lockfile

frontend-dev: ## Run Vite dev server (http://localhost:5173)
	cd frontend && pnpm dev

frontend-test: ## Run frontend unit tests (vitest)
	cd frontend && pnpm test

frontend-browser-integration: ## Run route-intercepted browser integration tests
	cd frontend && pnpm browser:integration

frontend-e2e-live-docker: ## Run no-mock Playwright smoke against the Docker stack
	docker compose up -d --build
	cd frontend && pnpm e2e:docker
