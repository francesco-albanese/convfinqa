.PHONY: up down aws-creds

up: ## Build and start the dockerised stack (Postgres + app)
	docker compose up -d --build

down: ## Stop and remove the dockerised stack
	docker compose down

aws-creds: ## Refresh STS credentials into .aws.env (uses AWS_PROFILE or sandbox-admin)
	aws configure export-credentials --profile $${AWS_PROFILE:-sandbox-admin} --format env-no-export > .aws.env
