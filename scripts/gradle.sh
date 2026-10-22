#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
docker run --rm --network host --user "$(id -u):$(id -g)" \
 -e GRADLE_USER_HOME=/cache \
 -e JAVA_TOOL_OPTIONS=-Djavax.net.ssl.trustStore=/trust/cacerts \
 -v "$ROOT/.runtime/cacerts:/trust/cacerts:ro" \
 -v "$ROOT/backend:/project" -v "$ROOT/.runtime/gradle:/cache" \
 -w /project gradle:8.14.3-jdk21 gradle --no-daemon --max-workers=2 "$@"
