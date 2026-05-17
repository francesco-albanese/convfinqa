SHELL := /bin/bash

AUTH_LAMBDA_DIR := auth-lambda

.PHONY: build-auth-lambda
build-auth-lambda: ## Bundle auth-lambda TS handlers (auth-lambda/dist/*.mjs)
	cd $(AUTH_LAMBDA_DIR) && pnpm install --frozen-lockfile && pnpm build

.PHONY: build-lambdas
build-lambdas: build-auth-lambda ## Build all lambda artifacts

.PHONY: clean-lambdas
clean-lambdas: ## Remove lambda build outputs
	rm -rf $(AUTH_LAMBDA_DIR)/dist
	rm -rf terraform/environmental/modules/compute/.build
	rm -f terraform/environmental/modules/keepalive/keepalive.zip
