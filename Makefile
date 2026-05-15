.DEFAULT_GOAL := help
SHELL := /bin/bash

PROJECT_NAME ?= convfinqa
ACCOUNT ?= sandbox
AWS_PROFILE ?= sandbox-admin

include makefiles/env.mk
include makefiles/test.mk
include makefiles/run.mk
include makefiles/docker.mk
include makefiles/frontend.mk
include makefiles/terraform.mk
include makefiles/lambdas.mk

.PHONY: help
help: ## Show available targets
	@grep -Eh '^[A-Za-z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
