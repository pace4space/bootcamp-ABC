#!/usr/bin/env bash
# Start Hellio HR dev environment.
# Usage: ./scripts/start-dev.sh [--build]
#
# Starts docker compose in the background, waits for the API to be healthy,
# then launches the Vite dev server in the foreground.
# Ctrl-C stops Vite; docker compose keeps running (use 'docker compose down' to stop).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

BUILD_FLAG=""
if [[ "${1:-}" == "--build" ]]; then
  BUILD_FLAG="--build"
fi

echo "==> Starting docker compose..."
docker compose up -d $BUILD_FLAG

echo "==> Waiting for API health check..."
MAX_WAIT=60
ELAPSED=0
until curl -sf http://localhost:8000/api/health > /dev/null 2>&1; do
  if (( ELAPSED >= MAX_WAIT )); then
    echo "ERROR: API did not become healthy within ${MAX_WAIT}s"
    echo "Check logs with: docker compose logs api"
    exit 1
  fi
  printf "."
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done
echo " ready"

echo ""
echo "  API:      http://localhost:8000"
echo "  Swagger:  http://localhost:8000/docs"
echo "  Frontend: http://localhost:5173  (starting now)"
echo ""
echo "  Credentials:  admin@hellio.com / admin123"
echo "                recruiter@hellio.com / recruit123"
echo "                viewer@hellio.com / view123"
echo ""
echo "  docker compose logs -f api   (in another terminal)"
echo "  docker compose down          (to stop backend)"
echo ""

/usr/bin/npm run dev
