#!/usr/bin/env bash
set -euo pipefail

# Creates one MercadoLibre SELLER TEST and one BUYER TEST user for a given site.
# Usage:
#   ML_APP_ID=xxx ML_CLIENT_SECRET=yyy ./marketplace_connector/scripts/create_ml_test_users.sh
# Optional:
#   SITE_ID=MLA (default)
#   OUTPUT_ENV_FILE=./marketplace_connector/.ml_test_users.env
#   OUTPUT_ODOO_PARAMS=1
#   OUTPUT_ODOO_FILE=./marketplace_connector/.ml_test_users.odoo.params

ML_API_BASE="https://api.mercadolibre.com"
SITE_ID="${SITE_ID:-MLA}"
APP_ID="${ML_APP_ID:-${CLIENT_ID:-}}"
APP_SECRET="${ML_CLIENT_SECRET:-${CLIENT_SECRET:-}}"
OUTPUT_ENV_FILE="${OUTPUT_ENV_FILE:-}"
OUTPUT_ODOO_PARAMS="${OUTPUT_ODOO_PARAMS:-0}"
OUTPUT_ODOO_FILE="${OUTPUT_ODOO_FILE:-}"

if [[ -z "$APP_ID" || -z "$APP_SECRET" ]]; then
  echo "Error: missing credentials." >&2
  echo "Set ML_APP_ID and ML_CLIENT_SECRET (or CLIENT_ID / CLIENT_SECRET)." >&2
  exit 1
fi

json_get() {
  local key="$1"
  python3 - "$key" <<'PY'
import json
import sys

key = sys.argv[1]
try:
    payload = json.load(sys.stdin)
except Exception:
    print("")
    sys.exit(0)

value = payload.get(key, "")
if value is None:
    value = ""
print(value)
PY
}

request_token() {
  curl -sS -X POST "$ML_API_BASE/oauth/token" \
    -H "accept: application/json" \
    -H "content-type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials&client_id=$APP_ID&client_secret=$APP_SECRET"
}

create_test_user() {
  local access_token="$1"
  curl -sS -X POST "$ML_API_BASE/users/test_user" \
    -H "Authorization: Bearer $access_token" \
    -H "Content-Type: application/json" \
    -d "{\"site_id\":\"$SITE_ID\"}"
}

echo "==> Getting app token..."
token_response="$(request_token)"
access_token="$(printf '%s' "$token_response" | json_get access_token)"

if [[ -z "$access_token" ]]; then
  echo "Error: could not get access token." >&2
  echo "Response: $token_response" >&2
  exit 1
fi

echo "==> Creating SELLER TEST user for site $SITE_ID..."
seller_response="$(create_test_user "$access_token")"
seller_id="$(printf '%s' "$seller_response" | json_get id)"
seller_nick="$(printf '%s' "$seller_response" | json_get nickname)"
seller_pass="$(printf '%s' "$seller_response" | json_get password)"

if [[ -z "$seller_id" ]]; then
  echo "Error: SELLER TEST creation failed." >&2
  echo "Response: $seller_response" >&2
  exit 1
fi

echo "==> Creating BUYER TEST user for site $SITE_ID..."
buyer_response="$(create_test_user "$access_token")"
buyer_id="$(printf '%s' "$buyer_response" | json_get id)"
buyer_nick="$(printf '%s' "$buyer_response" | json_get nickname)"
buyer_pass="$(printf '%s' "$buyer_response" | json_get password)"

if [[ -z "$buyer_id" ]]; then
  echo "Error: BUYER TEST creation failed." >&2
  echo "Response: $buyer_response" >&2
  exit 1
fi

echo
echo "MercadoLibre test users created successfully"
echo "SELLER_TEST_ID=$seller_id"
echo "SELLER_TEST_NICKNAME=$seller_nick"
echo "SELLER_TEST_PASSWORD=$seller_pass"
echo "BUYER_TEST_ID=$buyer_id"
echo "BUYER_TEST_NICKNAME=$buyer_nick"
echo "BUYER_TEST_PASSWORD=$buyer_pass"

odoo_params_block=$(cat <<EOF
sce_connector_ml.test.site_id=$SITE_ID
sce_connector_ml.test.seller_id=$seller_id
sce_connector_ml.test.seller_nickname=$seller_nick
sce_connector_ml.test.seller_password=$seller_pass
sce_connector_ml.test.buyer_id=$buyer_id
sce_connector_ml.test.buyer_nickname=$buyer_nick
sce_connector_ml.test.buyer_password=$buyer_pass
EOF
)

if [[ -n "$OUTPUT_ENV_FILE" ]]; then
  mkdir -p "$(dirname "$OUTPUT_ENV_FILE")"
  # Keep test credentials private in local environments.
  umask 077
  cat > "$OUTPUT_ENV_FILE" <<EOF
SITE_ID=$SITE_ID
SELLER_TEST_ID=$seller_id
SELLER_TEST_NICKNAME=$seller_nick
SELLER_TEST_PASSWORD=$seller_pass
BUYER_TEST_ID=$buyer_id
BUYER_TEST_NICKNAME=$buyer_nick
BUYER_TEST_PASSWORD=$buyer_pass
EOF
  echo
  echo "Saved credentials to $OUTPUT_ENV_FILE"
fi

if [[ "$OUTPUT_ODOO_PARAMS" == "1" ]]; then
  echo
  echo "Odoo system parameters (key=value):"
  echo "$odoo_params_block"
fi

if [[ -n "$OUTPUT_ODOO_FILE" ]]; then
  mkdir -p "$(dirname "$OUTPUT_ODOO_FILE")"
  # Keep test credentials private in local environments.
  umask 077
  printf '%s\n' "$odoo_params_block" > "$OUTPUT_ODOO_FILE"
  echo
  echo "Saved Odoo params to $OUTPUT_ODOO_FILE"
fi
