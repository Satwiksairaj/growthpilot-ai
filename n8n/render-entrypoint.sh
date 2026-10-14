#!/bin/sh
set -eu

if [ -n "${RENDER_EXTERNAL_HOSTNAME:-}" ]; then
  export N8N_HOST="$RENDER_EXTERNAL_HOSTNAME"
  export N8N_PROTOCOL="https"
  export N8N_EDITOR_BASE_URL="https://${RENDER_EXTERNAL_HOSTNAME}/"
  export WEBHOOK_URL="https://${RENDER_EXTERNAL_HOSTNAME}/"
fi

export N8N_PORT="${PORT:-5678}"
export N8N_LISTEN_ADDRESS="0.0.0.0"
export N8N_PROXY_HOPS="1"

exec n8n start
