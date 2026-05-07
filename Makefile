.DEFAULT_GOAL := help
SHELL := /bin/bash

include makefiles/env.mk

.PHONY: help
help: ## Show available targets
	@grep -Eh '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
