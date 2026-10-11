#!/usr/bin/env bash
set -euo pipefail
if [ -z "${1:-}" ]; then
  echo "Usage: $0 <backup.sql>"
  exit 1
fi
docker compose exec -T db psql -U postgres < "$1"
echo "Restore completed from $1"
