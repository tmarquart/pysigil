#!/usr/bin/env sh
set -eu
docker run --rm \
  -e SIGIL_SECRET_DEMO_SECRET_API_KEY=abc123 \
  sigil-test sigil get secret.api_key --app demo
