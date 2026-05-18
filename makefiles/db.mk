.PHONY: db-shell

db-shell: ## Open psql against Aurora in $(ACCOUNT) (override ACCOUNT=... or REGION=...)
	@set -euo pipefail; \
	  tmp=$$(mktemp -d); \
	  trap 'rm -rf "$$tmp"' EXIT; \
	  curl -fsS -o "$$tmp/ca.pem" https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem; \
	  url=$$(AWS_PROFILE=$(AWS_PROFILE) aws ssm get-parameter \
	    --name "/$(PROJECT_NAME)/$(ACCOUNT)/database_url" \
	    --with-decryption --region $(REGION) \
	    --query 'Parameter.Value' --output text); \
	  pw=$$(printf '%s' "$$url" | sed -E 's|.*://[^:]+:([^@]+)@.*|\1|'); \
	  host=$$(printf '%s' "$$url" | sed -E 's|.*@([^:]+):.*|\1|'); \
	  user=$$(printf '%s' "$$url" | sed -E 's|.*://([^:]+):.*|\1|'); \
	  db=$$(printf '%s'   "$$url" | sed -E 's|.*/([^/?]+)$$|\1|'); \
	  PGPASSWORD="$$pw" docker run --rm -it \
	    -e PGPASSWORD \
	    -v "$$tmp:/ca:ro" \
	    postgres:18.3-bookworm \
	    psql "host=$$host port=5432 dbname=$$db user=$$user sslmode=verify-full sslrootcert=/ca/ca.pem"
