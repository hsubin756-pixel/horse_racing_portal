#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/prepare-build.py
mkdir -p .runtime/gradle .runtime/npm ml/.wheels
./scripts/gradle.sh build
npm --prefix frontend ci --cache "$PWD/.runtime/npm" --no-audit --no-fund
npm --prefix frontend run build
# ML pins (numpy 2.2.6, scikit-learn 1.6.1) ship wheels for CPython 3.12/3.13 only. A newer system python3 (e.g. 3.14 on
# Ubuntu 26.04) would try to compile numpy from source, so pick a supported interpreter explicitly.
ML_PYTHON="${ML_PYTHON:-$(command -v python3.12 || command -v python3.13 || true)}"
if [ -z "$ML_PYTHON" ] && python3 -c 'import sys; sys.exit(sys.version_info[:2] not in ((3,12),(3,13)))'; then ML_PYTHON=python3; fi
if [ -z "$ML_PYTHON" ]; then
  echo "ML 가상환경에는 Python 3.12 또는 3.13이 필요합니다(현재 python3: $(python3 --version 2>&1))." >&2
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh && ~/.local/bin/uv python install 3.12" >&2
  echo "  ML_PYTHON=\$(~/.local/bin/uv python find 3.12) ./scripts/up.sh" >&2
  exit 1
fi
if [ -x .runtime/ml-venv/bin/python ] && ! .runtime/ml-venv/bin/python -c 'import sys; sys.exit(sys.version_info[:2] not in ((3,12),(3,13)))' 2>/dev/null; then
  rm -rf .runtime/ml-venv   # created by an unsupported interpreter in an earlier attempt
fi
"$ML_PYTHON" -m venv .runtime/ml-venv
.runtime/ml-venv/bin/pip install --cache-dir .runtime/pip -r ml/requirements.lock
# Wheels for the Docker image must match its interpreter (python:3.12-slim, glibc 2.36), not the host's.
rm -f ml/.wheels/*.whl
.runtime/ml-venv/bin/pip download --cache-dir .runtime/pip --only-binary=:all: --dest ml/.wheels \
  --python-version 3.12 --implementation cp --abi cp312 --abi none \
  --platform manylinux_2_17_x86_64 --platform manylinux2014_x86_64 --platform manylinux_2_27_x86_64 --platform manylinux_2_28_x86_64 --platform any \
  -r ml/requirements.lock
.runtime/ml-venv/bin/python scripts/hash-wheels.py
.runtime/ml-venv/bin/python ml/train.py
.runtime/ml-venv/bin/python -m unittest discover -s ml -p 'test_*.py' -v
