.PHONY: up down aws-creds seed-docs

up: ## Build and start the dockerised stack (Postgres + app + frontend)
	docker compose up -d --build

down: ## Stop and remove the dockerised stack
	docker compose down

aws-creds: ## Refresh STS credentials into .aws.env (uses AWS_PROFILE or sandbox-admin)
	aws configure export-credentials --profile $${AWS_PROFILE:-sandbox-admin} --format env-no-export > .aws.env

seed-docs: ## Seed the documents table from data/convfinqa_dataset.json (idempotent)
	uv run python backend/scripts/seed_documents.py
