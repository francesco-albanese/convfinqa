SHELL := /bin/bash

AUTH_LAMBDA_DIR := auth-lambda
KEEPALIVE_DIR   := terraform/environmental/modules/keepalive
KEEPALIVE_BUILD := $(KEEPALIVE_DIR)/build

.PHONY: build-auth-lambda
build-auth-lambda: ## Bundle auth-lambda TS handlers (auth-lambda/dist/*.mjs)
	cd $(AUTH_LAMBDA_DIR) && pnpm install --frozen-lockfile && pnpm build

.PHONY: build-keepalive
build-keepalive: ## Stage keepalive Python lambda + uv-installed deps
	rm -rf $(KEEPALIVE_BUILD)
	mkdir -p $(KEEPALIVE_BUILD)
	cp $(KEEPALIVE_DIR)/handler.py $(KEEPALIVE_BUILD)/
	uv pip install --python 3.13 --python-platform x86_64-manylinux2014 --target $(KEEPALIVE_BUILD) pg8000

.PHONY: build-lambdas
build-lambdas: build-auth-lambda build-keepalive ## Build all lambda artifacts consumed by data.archive_file

.PHONY: clean-lambdas
clean-lambdas: ## Remove lambda build outputs
	rm -rf $(AUTH_LAMBDA_DIR)/dist
	rm -rf $(KEEPALIVE_BUILD)
	rm -rf terraform/environmental/modules/compute/.build
	rm -rf terraform/environmental/modules/keepalive/.build
