#!/usr/bin/env bash
set -euo pipefail
: "${DATEPASS_URL:?Set DATEPASS_URL}"
: "${DATEPASS_CREATOR_KEY:?Set DATEPASS_CREATOR_KEY}"
curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  -H "X-DatePass-Creator-Key: ${DATEPASS_CREATOR_KEY}" \
  -d '{"recipient_name":"Test Passenger","date":"2026-06-14T20:00:00-06:00","place":"Coffee Lab","message":"A test flight into the Date Zone."}' \
  "${DATEPASS_URL%/}/invite"
echo
