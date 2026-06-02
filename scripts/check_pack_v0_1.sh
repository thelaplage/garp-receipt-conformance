#!/usr/bin/env bash
#
# check_pack_v0_1.sh — clean-checkout verification for the GARP/SRS receipt
# envelope conformance pack.
#
# This pack is a faithful, digest-pinned vendoring of the canonical ARCS SRS
# envelope schema, manifest, and validator from arcs-srs, plus the canonical
# conformance fixtures. It validates ARCS SRS *envelope* form only; it does not
# bless GARP body-kind semantics. See README.md and docs/ for what this does and
# does not establish.
#
# Runs end-to-end from a clean checkout using only the Python 3 standard library
# and stock POSIX tooling. No network access, no dependency install, no private
# corpus, no private repositories.
#
# Pack version marker: v0.1. Vendored schema version: v0.1.0. Receipt version
# carried by canonical receipts: srs.core.v5.1. These three are distinct.
#
# Usage (from the repository root):
#   bash scripts/check_pack_v0_1.sh
#
# Exit status:
#   0  all checks passed
#   non-zero  the first failing check aborted the run (fail-fast)

set -eu

# --- locate repo root and require invocation from it -----------------------

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ "$(pwd -P)" != "$REPO_ROOT" ]; then
    printf 'ERROR: run this script from the repository root: %s\n' "$REPO_ROOT" >&2
    exit 2
fi

SCHEMA="schemas/srs-envelope/v0.1.0/srs-envelope.schema.json"
MANIFEST="schemas/srs-envelope/v0.1.0/srs-envelope.schema.manifest.json"
SCHEMA_SHA="schemas/srs-envelope/v0.1.0/srs-envelope.schema.sha256"
VALIDATOR="tools/validate_srs_envelope.py"
VALID_DIR="fixtures/valid"
INVALID_DIR="fixtures/invalid"
EXPECTED_VALID_DIR="expected/valid"
EXPECTED_INVALID_DIR="expected/invalid"

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

python3 -m json.tool "$MANIFEST" >/dev/null
pass "schema manifest parses as JSON"

python3 -m json.tool "schemas/srs-envelope/v0.1.0/PROVENANCE.json" >/dev/null
pass "schema provenance parses as JSON"

python3 -m json.tool "fixtures/PROVENANCE.json" >/dev/null
pass "fixture provenance parses as JSON"

for fixture in "$VALID_DIR"/*.json "$INVALID_DIR"/*.json; do
    python3 -m json.tool "$fixture" >/dev/null
done
pass "all fixtures parse as JSON"

# --- 3. pinned schema digest matches --------------------------------------

shasum -c "$SCHEMA_SHA" >/dev/null
pass "schema digest matches $SCHEMA_SHA"

# --- 4. valid fixtures: validator passes (exit 0) and output matches -------

for fixture in "$VALID_DIR"/*.json; do
    base=$(basename "$fixture" .json)
    expected="$EXPECTED_VALID_DIR/$base.txt"
    out="$TMPDIR_WORK/valid-$base.out"
    set +e
    python3 "$VALIDATOR" "$fixture" >"$out"
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        printf 'ERROR: validator exit %d on valid fixture %s (expected 0)\n' "$rc" "$fixture" >&2
        exit 1
    fi
    diff -u "$expected" "$out"
    pass "valid fixture $base: exit 0 and output matches $expected"
done

# --- 5. invalid fixtures: validator fails (exit 1) and output matches ------

for fixture in "$INVALID_DIR"/*.json; do
    base=$(basename "$fixture" .json)
    expected="$EXPECTED_INVALID_DIR/$base.txt"
    out="$TMPDIR_WORK/invalid-$base.out"
    set +e
    python3 "$VALIDATOR" "$fixture" >"$out"
    rc=$?
    set -e
    if [ "$rc" -ne 1 ]; then
        printf 'ERROR: validator exit %d on invalid fixture %s (expected 1)\n' "$rc" "$fixture" >&2
        exit 1
    fi
    diff -u "$expected" "$out"
    pass "invalid fixture $base: exit 1 and output matches $expected"
done

# --- summary ---------------------------------------------------------------

printf 'PASS: receipt-envelope conformance pack v0.1 (%d checks)\n' "$step"
