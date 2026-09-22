#!/usr/bin/env bash
# Post-deploy smoke test for GraphIntel. Exercises the critical path against a
# running API and fails fast (non-zero exit) on any regression.
#
# Usage:
#   BASE=http://localhost:8000 bash infra/smoke_test.sh
#   BASE=http://<alb-dns> bash infra/smoke_test.sh
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"
echo "Smoke testing GraphIntel at ${BASE}"

fail() { echo "FAIL: $1" >&2; exit 1; }

# jq is used for assertions; fall back to grep if unavailable.
have_jq() { command -v jq >/dev/null 2>&1; }

echo "1/6 health"
curl -fsS "${BASE}/health" | grep -q '"status":"ok"' || fail "health not ok"

echo "2/6 ready"
READY=$(curl -fsS "${BASE}/ready")
echo "$READY" | grep -q '"status":"ready"' || fail "not ready: $READY"
echo "$READY" | grep -q '"production_safety_errors":\[\]' || fail "production safety errors: $READY"

echo "3/6 seed demo corpus"
curl -fsS -X POST "${BASE}/admin/seed" >/dev/null || fail "seed failed"

echo "4/6 stats populated"
STATS=$(curl -fsS "${BASE}/admin/stats")
if have_jq; then
  [ "$(echo "$STATS" | jq '.entities')" -gt 100 ] || fail "too few entities: $STATS"
else
  echo "$STATS" | grep -q '"entities"' || fail "no entities in stats"
fi

echo "5/6 grounded answer (not refused, has citations)"
ANS=$(curl -fsS -X POST "${BASE}/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"Which engineering team owns the service involved in INC-247?"}')
if have_jq; then
  CONF=$(echo "$ANS" | jq -r '.confidence')
  [ "$CONF" != "insufficient" ] || fail "answer refused: $ANS"
  [ "$(echo "$ANS" | jq '.citations | length')" -gt 0 ] || fail "no citations"
  [ "$(echo "$ANS" | jq '.reasoning_path | length')" -gt 0 ] || fail "no reasoning path"
else
  echo "$ANS" | grep -q '"citations"' || fail "no citations field"
fi

echo "6/6 release gate PASS"
GATE=$(curl -fsS "${BASE}/eval/release-gate")
if have_jq; then
  [ "$(echo "$GATE" | jq -r '.status')" = "PASS" ] || fail "release gate not PASS: $GATE"
else
  echo "$GATE" | grep -q '"status":"PASS"' || fail "release gate not PASS"
fi

echo "ALL SMOKE CHECKS PASSED"
