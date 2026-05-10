#!/usr/bin/env sh
set -eu

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "${REPO_ROOT}" ]; then
  echo "install-hooks: not inside a git repo, skipping." >&2
  exit 0
fi

HOOKS_PATH=$(git -C "${REPO_ROOT}" config --local --get core.hooksPath 2>/dev/null || true)

if [ -n "${HOOKS_PATH}" ]; then
  case "${HOOKS_PATH}" in
    /*) HOOKS_DIR="${HOOKS_PATH}" ;;
    *)  HOOKS_DIR="${REPO_ROOT}/${HOOKS_PATH}" ;;
  esac
  TARGET="${HOOKS_DIR}/pre-commit"

  if [ ! -f "${TARGET}" ]; then
    echo "install-hooks: ${TARGET} missing — run 'bd hooks install' first, skipping." >&2
    exit 0
  fi

  if grep -Fq 'BEGIN LEFTHOOK CHAIN (frontend)' "${TARGET}"; then
    exit 0
  fi

  cat >> "${TARGET}" <<'CHAIN'

# --- BEGIN LEFTHOOK CHAIN (frontend) ---
# Chained because beads owns core.hooksPath. Runs lefthook from frontend/
# so frontend/node_modules/.bin/lefthook resolves; lefthook discovers
# the repo-root lefthook.yml on its own. Maintained by
# frontend/scripts/install-hooks.sh — re-run after `bd hooks install`.
if [ -f "$(git rev-parse --show-toplevel)/lefthook.yml" ] \
  && [ -x "$(git rev-parse --show-toplevel)/frontend/node_modules/.bin/lefthook" ]; then
  (cd "$(git rev-parse --show-toplevel)/frontend" && pnpm exec lefthook run pre-commit "$@")
  _lh_exit=$?
  if [ $_lh_exit -ne 0 ]; then exit $_lh_exit; fi
fi
# --- END LEFTHOOK CHAIN (frontend) ---
CHAIN
  echo "install-hooks: chained lefthook into ${TARGET}"
  exit 0
fi

cd "${REPO_ROOT}/frontend"
pnpm exec lefthook install
