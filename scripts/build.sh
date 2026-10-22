#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/prepare-build.py
mkdir -p .runtime/gradle .runtime/npm ml/.wheels
./scripts/gradle.sh build
npm --prefix frontend ci --cache "$PWD/.runtime/npm" --no-audit --no-fund
npm --prefix frontend run build
python3 -m venv .runtime/ml-venv
.runtime/ml-venv/bin/pip install --cache-dir .runtime/pip -r ml/requirements.lock
.runtime/ml-venv/bin/pip download --cache-dir .runtime/pip --only-binary=:all: --dest ml/.wheels -r ml/requirements.lock
.runtime/ml-venv/bin/python scripts/hash-wheels.py
.runtime/ml-venv/bin/python ml/train.py
.runtime/ml-venv/bin/python -m unittest discover -s ml -p 'test_*.py' -v
