#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export DOCKER_CONFIG="$PWD/.runtime/docker"
mkdir -p "$DOCKER_CONFIG"
python3 scripts/init-env.py
./scripts/build.sh
docker compose up -d --build
python3 scripts/wait-ready.py
