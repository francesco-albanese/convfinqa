SHELL := /bin/bash

AUTH_LAMBDA_DIR := auth-lambda
KEEPALIVE_DIR   := terraform/environmental/modules/keepalive

.PHONY: build-auth-lambda
build-auth-lambda: ## Bundle auth-lambda TS handlers (auth-lambda/dist/*.mjs)
	cd $(AUTH_LAMBDA_DIR) && pnpm install --frozen-lockfile && pnpm build

.PHONY: build-keepalive
build-keepalive: ## Build keepalive container image (linux/amd64)
	docker build --platform linux/amd64 -t keepalive:local $(KEEPALIVE_DIR)/

.PHONY: build-lambdas
build-lambdas: build-auth-lambda build-keepalive ## Build all lambda artifacts

.PHONY: clean-lambdas
clean-lambdas: ## Remove lambda build outputs
	rm -rf $(AUTH_LAMBDA_DIR)/dist
	rm -rf terraform/environmental/modules/compute/.build
	docker rmi keepalive:local 2>/dev/null || true
