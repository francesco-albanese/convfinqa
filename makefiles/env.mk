.PHONY: sync install-hooks

sync: ## Sync virtual environment with uv
	uv sync

install-hooks: ## Install prek pre-commit hooks (idempotent)
	bash scripts/install-prek-hook.sh
