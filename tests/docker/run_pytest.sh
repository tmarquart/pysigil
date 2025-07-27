#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(dirname "$0")"
docker build -t sigil-test -f "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR/../.."
docker run --rm sigil-test pytest -q
