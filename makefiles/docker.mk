.PHONY: up down seed-docs

up: ## Build and start the local stack (Postgres + app + frontend)
	docker compose up -d --build --remove-orphans

down: ## Stop and remove the local stack
	docker compose down

seed-docs: ## Seed the local documents table (idempotent)
	uv run python backend/scripts/seed_documents.py
