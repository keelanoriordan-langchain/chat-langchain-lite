#!/usr/bin/env bash
#
# Start Chat LangChain Lite with the ambient ANTHROPIC_* variables stripped.
#
# External tooling injects ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL /
# ANTHROPIC_CUSTOM_HEADERS into the shell. The `anthropic` SDK reads
# ANTHROPIC_CUSTOM_HEADERS (see anthropic/_client.py:231) and merges it into the
# default headers of every request, and it reads ANTHROPIC_BASE_URL too — so a
# stray X-Api-Key header or base URL hijacks the LangSmith Gateway route that
# utils/models.py configures explicitly. Clear them before the app imports the SDK.
#
# Usage:  ./start.sh            # serves the UI at http://localhost:2024/
#         ./start.sh --port 8000
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

unset ANTHROPIC_API_KEY
unset ANTHROPIC_CUSTOM_HEADERS
unset ANTHROPIC_BASE_URL
unset ANTHROPIC_AUTH_TOKEN

echo "→ cleared: ANTHROPIC_API_KEY, ANTHROPIC_CUSTOM_HEADERS, ANTHROPIC_BASE_URL, ANTHROPIC_AUTH_TOKEN"

# utils/models.py calls load_dotenv(dotenv_path="../.env", override=True), so a
# parent-directory .env can put these back *after* the unsets above. Warn with
# variable names only — never their values.
if [ -f ../.env ] && grep -qE '^[[:space:]]*ANTHROPIC_' ../.env; then
  names=$(grep -oE '^[[:space:]]*ANTHROPIC_[A-Z_]+' ../.env | tr -d '[:space:]' | sort -u | paste -sd', ' -)
  echo "⚠  $(cd .. && pwd)/.env re-sets: ${names}"
  echo "   utils/models.py loads it with override=True, so it wins over the unset above."
  echo "   The model call is unaffected (api_key/base_url are passed explicitly),"
  echo "   but the variables will be present in the process env."
fi

exec uv run langgraph dev "$@"
