#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=${REPO_DIR:-/opt/aria}
DOMAIN=${ARIA_DOMAIN:-}

if [[ -z "$DOMAIN" ]]; then
  echo "Set ARIA_DOMAIN first."
  exit 1
fi

cd "$REPO_DIR/cloud"

if [[ ! -f .env ]]; then
  echo "Create cloud/.env from cloud/.env.example first."
  exit 1
fi

docker compose pull
docker compose build
docker compose up -d
sleep 5
curl -fsS http://127.0.0.1:8000/status || true

echo "ARIA cloud started: https://$DOMAIN"
