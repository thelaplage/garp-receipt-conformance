#!/usr/bin/env bash
#
# check.sh -- conformance check for the SAM execution-receipt pack
# (SAM-EXECUTION-RECEIPT0, DRAFT, AUTHORITY_MOVEMENT=0).
#
# This pack profiles a PORTABLE EXECUTION RECEIPT for one remote MCP tool
# invocation carried over SAM (the first transport adapter this shape is
# proven for). It does NOT invent a new receipt family: it EXTENDS the
# existing closed-enum `sdk_enforcement` receipt_type with a new GARP
# body_kind, `sam_execution_receipt`, carried under extensions.garp.body
# exactly like every other pack in this repo.
#
# This is explicit-file-input only. No SAM/DAGR-MCP process is run, no
# network is touched, no credentials are read: a repo-wide search at
# authoring time found no live "SAM" transport implementation anywhere in
# this repo or any sibling GARP/ARCS/DAGR repo, so every input file here is a
# public-safe, SYNTHETIC projection of what such a transport's observations
# would contain -- the same discipline already established by
# packs/mcp-audit-trail/v0.1/ and packs/bedrock-openai-audit/v0.1/.
#
# It proves, in order:
#   1. all four outcome adapters (success / refused / transport_failure /
#      contaminated_response) regenerate their receipts byte-identically from
#      their explicit input files,
#   2. each regenerated receipt cryptographically binds the exact input bytes,
#   3. each of the four outcome receipts validates against the canonical SRS
#      envelope schema already vendored in this repo (envelope form only),
#   4. a canonical body-verdict drift fixture is rejected by that same
#      canonical validator (TOP_LEVEL_BODY_VERDICT),
#   5. the SAM standing-injection fixtures (verified/published/admitted/
#      authority-grant/evidence-support injection) all PASS the canonical
#      envelope validator -- proving that layer alone cannot catch this
#      class of drift for this body_kind -- and then runs the portable
#      standalone verifier, which:
#        - recomputes a deterministic, reordering-stable receipt identity,
#        - rejects every one of those standing-injection fixtures,
#        - detects a mutated argument/payload digest as an invalid,
#          mismatched receipt,
#        - verifies all four outcome receipts end-to-end,
#   6. the parity + guard test proves the standalone verifier's vendored
#      envelope logic has not diverged from the canonical in-repo validator.
#
# It validates STRUCTURAL and CRYPTOGRAPHIC integrity only. receipt_valid !=
# action_authorized, receipt_valid != output_true, receipt_valid !=
# output_evidence_supported, receipt_valid != admitted, receipt_valid !=
# published. See README.md.
#
# No network, no live credentials, no scanner, no private corpus, no live
# SAM/DAGR-MCP integration. Python 3 standard library and stock POSIX tooling
# only.
#
# Usage (from the repository root):
#   bash packs/sam-execution-receipt/v0.1/check.sh
#
# Exit status: 0 all checks passed; non-zero the first failing check aborted.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)

if [ "$(pwd -P)" != "$REPO_ROOT" ]; then
    printf 'ERROR: run this script from the repository root: %s\n' "$REPO_ROOT" >&2
    exit 2
fi

PACK="packs/sam-execution-receipt/v0.1"
VALIDATOR="tools/validate_srs_envelope.py"
ADAPTER="$PACK/tools/build_receipt.py"
STANDALONE="$PACK/tools/verify_standalone.py"
STANDALONE_TEST="$PACK/tools/test_verify_standalone.py"
SCHEMA="schemas/srs-envelope/v0.1.0/srs-envelope.schema.json"
MANIFEST="schemas/srs-envelope/v0.1.0/srs-envelope.schema.manifest.json"

OUTCOMES="success refused transport_failure contaminated"
DRIFT="$PACK/fixtures/invalid/top_level_status_verdict.json"
EXPECTED_DRIFT="$PACK/expected/invalid/top_level_status_verdict.txt"
INJECTION_FIXTURES="top_level_verified_true top_level_published_true body_admitted_true body_authority_grant body_evidence_support_injection"

TMPDIR_WORK=$(mktemp -d "${TMPDIR:-/tmp}/check_sam_execution_receipt.XXXXXX")
cleanup() {
    rm -rf "$TMPDIR_WORK"
}
trap cleanup EXIT INT TERM

step=0
pass() {
    step=$((step + 1))
    printf 'ok %d - %s\n' "$step" "$1"
}

# --- 1. no unstaged whitespace/conflict damage ------------------------------

git diff --check
pass "git diff --check (no whitespace/conflict damage)"

# --- 2. all pack JSON artifacts parse ---------------------------------------

for outcome in $OUTCOMES; do
    python3 -m json.tool "$PACK/input/sam_execution_${outcome}.input.json" >/dev/null
    python3 -m json.tool "$PACK/fixtures/valid/sam_execution_${outcome}.envelope.json" >/dev/null
done
for name in $INJECTION_FIXTURES; do
    python3 -m json.tool "$PACK/fixtures/invalid/${name}.json" >/dev/null
done
python3 -m json.tool "$DRIFT" >/dev/null
python3 -m json.tool "$PACK/PROVENANCE.json" >/dev/null
pass "input, fixtures, and provenance parse as JSON"

# --- 3. every outcome adapter regenerates byte-identically ------------------

for outcome in $OUTCOMES; do
    REGEN="$TMPDIR_WORK/${outcome}.regenerated.json"
    python3 "$ADAPTER" "$PACK/input/sam_execution_${outcome}.input.json" --out "$REGEN"
    diff -u "$PACK/fixtures/valid/sam_execution_${outcome}.envelope.json" "$REGEN"
done
pass "all four outcome receipts regenerate byte-identically from their inputs"

# --- 4. each outcome receipt cryptographically binds its input bytes -------

for outcome in $OUTCOMES; do
    python3 - "$PACK/input/sam_execution_${outcome}.input.json" \
        "$PACK/fixtures/valid/sam_execution_${outcome}.envelope.json" \
        "sam_execution_${outcome}.input.json" <<'PY'
import hashlib, json, sys
input_path, receipt_path, label = sys.argv[1], sys.argv[2], sys.argv[3]
actual = "sha256:" + hashlib.sha256(open(input_path, "rb").read()).hexdigest()
receipt = json.load(open(receipt_path))
recorded = receipt["extensions"]["garp"]["body"]["artifact_hashes"][f"input/{label}"]
if actual != recorded:
    sys.stderr.write(f"input digest {actual} != recorded {recorded}\n")
    sys.exit(1)
PY
done
pass "each outcome receipt's artifact_hashes matches the sha256 of its input bytes"

# --- 5. each outcome receipt: canonical validator passes (exit 0) ----------

for outcome in $OUTCOMES; do
    out="$TMPDIR_WORK/${outcome}.canonical.out"
    set +e
    python3 "$VALIDATOR" "$PACK/fixtures/valid/sam_execution_${outcome}.envelope.json" >"$out"
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        printf 'ERROR: canonical validator exit %d on %s (expected 0)\n' "$rc" "$outcome" >&2
        exit 1
    fi
    diff -u "$PACK/expected/valid/sam_execution_${outcome}.envelope.txt" "$out"
done
pass "all four outcome receipts: canonical validator exit 0, output matches expected/valid/"

# --- 6. canonical drift fixture: canonical validator fails (exit 1) --------

out="$TMPDIR_WORK/drift.canonical.out"
set +e
python3 "$VALIDATOR" "$DRIFT" >"$out"
rc=$?
set -e
if [ "$rc" -ne 1 ]; then
    printf 'ERROR: canonical validator exit %d on drift fixture (expected 1)\n' "$rc" >&2
    exit 1
fi
diff -u "$EXPECTED_DRIFT" "$out"
pass "canonical drift fixture: exit 1 and output matches $EXPECTED_DRIFT"

# --- 7. standing-injection fixtures PASS the canonical validator -----------
#
# This is the point of the pack: for this body_kind, verified/published/
# admitted/authority-grant/evidence-support injection is envelope-VALID.
# Only the pack-local SAM standing-injection guardrail (step 8 below) catches
# it. If any of these ever started failing the canonical validator, that
# would silently narrow what this pack is proving -- fail loudly instead.

for name in $INJECTION_FIXTURES; do
    set +e
    python3 "$VALIDATOR" "$PACK/fixtures/invalid/${name}.json" >/dev/null
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        printf 'ERROR: canonical validator unexpectedly rejected %s (exit %d); ' "$name" "$rc" >&2
        printf 'this pack asserts canonical envelope checks alone cannot catch this injection class\n' >&2
        exit 1
    fi
done
pass "standing-injection fixtures are canonical-envelope-valid (guardrail gap is real, not fixture error)"

# --- 8. portable standalone verifier: SAM standing-injection guardrail -----
#
# 8a. stdlib-only (no product/network imports).
if grep -Eq '^[[:space:]]*(from[[:space:]]+(garp_core|garp_sdk|arcs_amnesiac|dagr_mcp|requests|urllib|http|socket|boto3|openai)|import[[:space:]]+(garp_core|garp_sdk|arcs_amnesiac|dagr_mcp|requests|urllib|http|socket|boto3|openai))' "$STANDALONE"; then
    printf 'ERROR: standalone verifier imports forbidden product/network module\n' >&2
    exit 1
fi
pass "standalone verifier imports no product/network module (stdlib only)"

# 8b. all four outcome receipts verify end-to-end (exit 0).
for outcome in $OUTCOMES; do
    set +e
    python3 "$STANDALONE" \
        --receipt "$PACK/fixtures/valid/sam_execution_${outcome}.envelope.json" \
        --input "$PACK/input/sam_execution_${outcome}.input.json" \
        --schema "$SCHEMA" \
        --manifest "$MANIFEST" >"$TMPDIR_WORK/${outcome}.standalone.out"
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        printf 'ERROR: standalone verifier exit %d on %s (expected 0)\n' "$rc" "$outcome" >&2
        exit 1
    fi
    grep -q 'Result: VERIFIED' "$TMPDIR_WORK/${outcome}.standalone.out"
done
pass "standalone verifier: all four outcome receipts verify end-to-end (exit 0, Result: VERIFIED)"

# 8c. every standing-injection fixture fails the standalone verifier (exit 1).
for name in $INJECTION_FIXTURES; do
    set +e
    python3 "$STANDALONE" \
        --receipt "$PACK/fixtures/invalid/${name}.json" \
        --input "$PACK/input/sam_execution_success.input.json" \
        --schema "$SCHEMA" \
        --manifest "$MANIFEST" >"$TMPDIR_WORK/${name}.standalone.out"
    rc=$?
    set -e
    if [ "$rc" -ne 1 ]; then
        printf 'ERROR: standalone verifier exit %d on %s (expected 1)\n' "$rc" "$name" >&2
        exit 1
    fi
    grep -q 'Result: NOT VERIFIED' "$TMPDIR_WORK/${name}.standalone.out"
    grep -q 'SAM standing-injection guardrails hold' "$TMPDIR_WORK/${name}.standalone.out"
done
pass "standalone verifier: every standing-injection fixture fails end-to-end (exit 1, guardrail cited)"

# 8d. the canonical-drift fixture also fails the standalone verifier.
set +e
python3 "$STANDALONE" \
    --receipt "$DRIFT" \
    --input "$PACK/input/sam_execution_success.input.json" \
    --schema "$SCHEMA" \
    --manifest "$MANIFEST" >"$TMPDIR_WORK/drift.standalone.out"
rc=$?
set -e
if [ "$rc" -ne 1 ]; then
    printf 'ERROR: standalone verifier exit %d on drift fixture (expected 1)\n' "$rc" >&2
    exit 1
fi
pass "standalone verifier: canonical-drift fixture also fails (exit 1)"

# --- 9. parity + guard test -------------------------------------------------
#
# Proves: (a) the standalone verifier's vendored envelope checks stay aligned
# with the canonical in-repo validator, (b) deterministic receipt identity is
# invariant under field reordering, (c) argument/payload digest mutation
# invalidates a mismatched receipt.
python3 "$STANDALONE_TEST"
pass "parity + guard test passes (envelope non-divergence, reordering stability, digest-mutation detection)"

# --- 10. AUTHORITY_MOVEMENT posture guard -----------------------------------
#
# This pack must never itself assert admission, verification, or publication.
# Grep the adapter and verifier source for accidental hard-coded assertions of
# the exact standing values the pack's own guardrails forbid receipts from
# carrying.
if grep -En '"(admitted|verified|published)":[[:space:]]*True' "$ADAPTER" "$STANDALONE" >/dev/null; then
    printf 'ERROR: pack source asserts a forbidden standing value directly\n' >&2
    exit 1
fi
pass "AUTHORITY_MOVEMENT=0 posture guard: no forbidden standing assertion in pack source"

# --- summary -----------------------------------------------------------------

printf 'PASS: SAM execution-receipt pack v0.1 (%d checks)\n' "$step"
