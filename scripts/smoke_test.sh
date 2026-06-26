#!/usr/bin/env bash
set -euo pipefail
: "${DATEPASS_URL:?Set DATEPASS_URL}"
: "${CREATOR_API_KEY:=${DATEPASS_CREATOR_KEY:-}}"
: "${CREATOR_API_KEY:?Set CREATOR_API_KEY}"
curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  -H "X-DatePass-Creator-Key: ${CREATOR_API_KEY}" \
  -d '{"recipient_name":"Test Passenger","date":"2026-06-14T20:00:00-06:00","place":"Coffee Lab","message":"A test flight into the Date Zone."}' \
  "${DATEPASS_URL%/}/invite"
echo
