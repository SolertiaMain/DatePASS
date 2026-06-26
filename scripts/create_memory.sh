#!/usr/bin/env bash
set -euo pipefail

: "${DATEPASS_URL:?Set DATEPASS_URL, for example https://hlstozop1b.execute-api.us-east-1.amazonaws.com/prod}"

if [[ -z "${CREATOR_API_KEY:-}" && -f "secret.json" ]]; then
  CREATOR_API_KEY="$(python -c 'import json; print(json.load(open("secret.json"))["creator_api_key"])')"
  export CREATOR_API_KEY
fi

: "${CREATOR_API_KEY:?Set CREATOR_API_KEY or keep a local secret.json with creator_api_key}"
: "${DATE_PHOTO:?Set DATE_PHOTO to a real JPEG or PNG path}"

case "$CREATOR_API_KEY" in
  TU_CREATOR_API_KEY_REAL|YOUR_API_KEY|changeme|copy-from-secrets-manager|copy-the-generated-creator-key)
    echo "Error: CREATOR_API_KEY still contains a documentation placeholder." >&2
    exit 1
    ;;
esac

if [[ ${#CREATOR_API_KEY} -lt 32 ]]; then
  echo "Error: CREATOR_API_KEY is missing or too short." >&2
  exit 1
fi

if [[ ! -f "$DATE_PHOTO" ]]; then
  echo "Error: photo not found: $DATE_PHOTO" >&2
  exit 1
fi

response_file="$(mktemp)"
trap 'rm -f "$response_file"' EXIT

status_code="$(
  curl --silent --show-error --output "$response_file" --write-out "%{http_code}" -X POST "${DATEPASS_URL%/}/memories" \
  -H "X-DatePass-Creator-Key: $CREATOR_API_KEY" \
  -F "recipient_name=${RECIPIENT_NAME:-Coco}" \
  -F "title=${MEMORY_TITLE:-Our First Date}" \
  -F "date=${MEMORY_DATE:-2026-06-23T13:00:00-06:00}" \
  -F "place=${MEMORY_PLACE:-Nolitas, 1pm}" \
  -F "message=${MEMORY_MESSAGE:-He preparado este recuerdo de nuestra primera cita oficial.}" \
  -F "memory_number=${MEMORY_NUMBER:-1}" \
  -F "theme=${MEMORY_THEME:-midnight-romance}" \
  -F "photo=@${DATE_PHOTO}"
)"

cat "$response_file"
echo

if [[ "$status_code" -lt 200 || "$status_code" -ge 300 ]]; then
  echo "Error: DatePass API returned HTTP $status_code" >&2
  exit 1
fi
