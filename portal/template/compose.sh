#!/bin/bash
export PORTAL_DOMAIN=""
export PORTAL_SERVICE_HOST=""
export CLOUDFLARE_API_TOKEN=""
export CLOUDFLARE_EMAIL=""
export TS_AUTHKEY=""

docker compose "$@"