.PHONY: run cli prompts-sync

run: ## Start the FastAPI server (uv run main)
	uv run main

cli: ## Run the Typer CLI; pass args via ARGS="..."
	uv run convfinqa $(ARGS)

prompts-sync: ## Publish the git-committed prompt catalog to Langfuse
	uv run convfinqa prompts sync
