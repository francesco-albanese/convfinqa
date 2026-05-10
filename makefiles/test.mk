.PHONY: test-unit test-integration test

test-unit: ## Run fast unit tests (no testcontainers)
	uv run pytest -m unit -q backend/tests/

test-integration: ## Run testcontainer-backed integration tests
	uv run pytest -m integration -q backend/tests/

test: test-unit test-integration ## Run unit tests, then integration tests
