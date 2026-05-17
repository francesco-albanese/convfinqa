#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -gt 0 ]; then
	exec "$@"
fi

alembic upgrade head
python -m convfinqa.adapters.persistence.documents_seeder

# exec replaces the shell with uvicorn so SIGTERM from `docker stop` reaches
# uvicorn directly (PID 1) for graceful shutdown. --host/--port hard-coded:
# the container's network contract is fixed at 0.0.0.0:8000 and the
# orchestrator maps externally; Settings.api_host default (127.0.0.1) stays
# safe for the host workflow.
exec uvicorn convfinqa.main:create_app --factory --host 0.0.0.0 --port 8000
