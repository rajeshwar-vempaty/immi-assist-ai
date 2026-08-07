#!/usr/bin/env bash
# Smoke-test a public Beacon deployment.
# Usage: ./scripts/public_launch_smoke.sh https://immiassist.example.com
set -euo pipefail

BASE="${1:-}"
if [[ -z "$BASE" ]]; then
  echo "Usage: $0 https://your-domain.example" >&2
  exit 2
fi

BASE="${BASE%/}"
API="$BASE/api/v1"
FAIL=0

check() {
  local name="$1"
  local url="$2"
  local want="$3"
  local code
  code=$(curl -sS -o /tmp/beacon_smoke_body.json -w "%{http_code}" "$url" || echo "000")
  if [[ "$code" == "$want" ]]; then
    echo "OK  $name ($code) $url"
  else
    echo "FAIL $name (got $code, want $want) $url" >&2
    FAIL=1
  fi
}

echo "Beacon public launch smoke → $BASE"
check "liveness" "$API/health/live" "200"
check "readiness" "$API/health/ready" "200"
check "docs blocked" "$BASE/docs" "404"
check "metrics blocked at edge" "$BASE/metrics" "404"

if [[ -f /tmp/beacon_smoke_body.json ]]; then
  # Re-fetch ready body for mode summary (best-effort).
  ready=$(curl -sS "$API/health/ready" || true)
  echo "ready payload: $ready"
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' "$ready" || true
import json, sys
try:
    data = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
mode = data.get("knowledge_base_mode")
req = data.get("require_scraped_kb")
print(f"knowledge_base_mode={mode} require_scraped_kb={req}")
if req and mode != "scraped":
    print("WARNING: REQUIRE_SCRAPED_KB is on but mode is not scraped", file=sys.stderr)
    sys.exit(1)
PY
  fi
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "Smoke failed." >&2
  exit 1
fi
echo "Smoke passed."
