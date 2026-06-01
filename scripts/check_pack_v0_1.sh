#!/usr/bin/env bash
#
# check_pack_v0_1.sh — Stage C5 clean-checkout verification for the GARP/SRS
# receipt envelope conformance pack v0.1.
#
# Runs the full public pack end-to-end from a clean checkout using only the
# Python 3 standard library and stock POSIX tooling. No network access, no
# dependency install, no private corpus, no private repositories.
#
# Usage (from the repository root):
#   bash scripts/check_pack_v0_1.sh
#
# Exit status:
#   0  all checks passed
#   non-zero  the first failing check aborted the run (fail-fast)
#
# See docs/CLEAN_CHECKOUT_V0_1.md for what this does and does not establish.

set -eu

# --- locate repo root and require invocation from it -----------------------

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ "$(pwd -P)" != "$REPO_ROOT" ]; then
    printf 'ERROR: run this script from the repository root: %s\n' "$REPO_ROOT" >&2
    exit 2
fi

SCHEMA="schemas/receipt-envelope-v0.1.schema.json"
SCHEMA_SHA="schemas/receipt-envelope-v0.1.sha256"
VALID_FIXTURE="fixtures/valid/receipt-envelope-minimal-v0.1.json"
INVALID_FIXTURE="fixtures/invalid/receipt-envelope-missing-body-v0.1.json"
VALIDATOR="validator/validate_receipt_envelope_v0_1.py"
VALID_EXPECTED="expected/valid-receipt-envelope-minimal-v0.1.txt"
INVALID_EXPECTED="expected/invalid-receipt-envelope-missing-body-v0.1.txt"

# --- safe temporary workspace, cleaned up on any exit ----------------------

TMPDIR_WORK=$(mktemp -d "${TMPDIR:-/tmp}/check_pack_v0_1.XXXXXX")
cleanup() {
    rm -rf "$TMPDIR_WORK"
}
trap cleanup EXIT INT TERM

step=0
pass() {
    step=$((step + 1))
    printf 'ok %d - %s\n' "$step" "$1"
}

# --- 1. no unstaged whitespace/conflict damage -----------------------------

git diff --check
pass "git diff --check (no whitespace/conflict damage)"

# --- 2. all JSON artifacts parse (stdlib json.tool) ------------------------

python3 -m json.tool "$SCHEMA" >/dev/null
pass "schema parses as JSON"

python3 -m json.tool "$VALID_FIXTURE" >/dev/null
pass "valid fixture parses as JSON"

python3 -m json.tool "$INVALID_FIXTURE" >/dev/null
pass "invalid fixture parses as JSON"

# --- 3. pinned schema digest matches --------------------------------------

shasum -c "$SCHEMA_SHA" >/dev/null
pass "schema digest matches $SCHEMA_SHA"

# --- 4. valid fixture: validator passes and output matches expected --------

valid_out="$TMPDIR_WORK/valid.out"
set +e
python3 "$VALIDATOR" "$VALID_FIXTURE" >"$valid_out"
valid_rc=$?
set -e
if [ "$valid_rc" -ne 0 ]; then
    printf 'ERROR: validator exit %d on valid fixture (expected 0)\n' "$valid_rc" >&2
    exit 1
fi
diff -u "$VALID_EXPECTED" "$valid_out"
pass "valid fixture: exit 0 and output matches $VALID_EXPECTED"

# --- 5. invalid fixture: validator fails (exit 1) and output matches -------

invalid_out="$TMPDIR_WORK/invalid.out"
set +e
python3 "$VALIDATOR" "$INVALID_FIXTURE" >"$invalid_out"
invalid_rc=$?
set -e
if [ "$invalid_rc" -ne 1 ]; then
    printf 'ERROR: validator exit %d on invalid fixture (expected 1)\n' "$invalid_rc" >&2
    exit 1
fi
diff -u "$INVALID_EXPECTED" "$invalid_out"
pass "invalid fixture: exit 1 and output matches $INVALID_EXPECTED"

# --- summary ---------------------------------------------------------------

printf 'PASS: receipt-envelope conformance pack v0.1 (%d checks)\n' "$step"
