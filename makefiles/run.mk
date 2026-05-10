.PHONY: run cli

run: ## Start the FastAPI server (uv run main)
	uv run main

cli: ## Run the Typer CLI; pass args via ARGS="..."
	uv run convfinqa $(ARGS)
