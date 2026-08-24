#!/usr/bin/env bash
#
# check.sh — conformance check for the receipt-witness pack (RECEIPT-WITNESS0).
#
# A ReceiptWitnessObservation is a signed claim that a witness node observed
# exact receipt bytes (by digest) by a stated time. This pack proves:
#
#   1. every JSON artifact in the pack parses,
#   2. three independent witness fixtures, observing the SAME receipt digest
#      at three distinct times, each verify as valid byte-observations,
#   3. each invalid fixture is rejected for exactly its one stated reason,
#   4. the derived witness-set aggregation is deterministic and
#      order-independent (build it from the fixtures in two different orders
#      and require byte-identical output), and
#   5. the repo-level regression script (scripts/check_receipt_witness.py)
#      still passes.
#
# Required invariant (see docs/dispatch/RECEIPT-WITNESS0.md):
#   witnessed_bytes != valid_receipt != authorized_action != true_result
#   != admitted_evidence
#
# This pack proves BYTE-OBSERVATION VALIDITY ONLY. It does NOT assert receipt
# validity, action authorization, factual truth, or admission, and witness
# count is never truth-from-count. No blockchain, no consensus protocol, no
# global timestamp authority is introduced anywhere in this pack.
#
# No network, no live credentials, no scanner, no private corpus. Python 3
# standard library and stock POSIX tooling only.
#
# Usage (from the repository root):
#   bash packs/receipt-witness/v0.1/check.sh
#
# Exit status: 0 all checks passed; non-zero the first failing check aborted.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)

if [ "$(pwd -P)" != "$REPO_ROOT" ]; then
    printf 'ERROR: run this script from the repository root: %s\n' "$REPO_ROOT" >&2
    exit 2
fi

PACK="packs/receipt-witness/v0.1"
VERIFIER="$PACK/tools/verify_witness.py"

VALID_FIXTURES="witness_a witness_b witness_c"
INVALID_FIXTURES="invalid_digest_format signature_incomplete authority_effect_violation witness_node_too_short additional_property_verdict observed_at_not_utc"

TMPDIR_WORK=$(mktemp -d "${TMPDIR:-/tmp}/check_receipt_witness.XXXXXX")
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

# --- 2. all pack + schema JSON artifacts parse ------------------------------

for name in $VALID_FIXTURES; do
    python3 -m json.tool "$PACK/fixtures/valid/$name.json" >/dev/null
done
for name in $INVALID_FIXTURES; do
    python3 -m json.tool "$PACK/fixtures/invalid/$name.json" >/dev/null
done
python3 -m json.tool schemas/receipt-witness-observation.v0.1.json >/dev/null
python3 -m json.tool "$PACK/PROVENANCE.json" >/dev/null
pass "fixtures, schema, and provenance parse as JSON"

# --- 3. each valid fixture: verifier exit 0, output matches expected -------

for name in $VALID_FIXTURES; do
    out="$TMPDIR_WORK/$name.out"
    set +e
    python3 "$VERIFIER" "$PACK/fixtures/valid/$name.json" >"$out"
    rc=$?
    set -e
    if [ "$rc" -ne 0 ]; then
        printf 'ERROR: verifier exit %d on valid fixture %s (expected 0)\n' "$rc" "$name" >&2
        exit 1
    fi
    diff -u "$PACK/expected/valid/$name.txt" "$out"
done
pass "three independent witness fixtures each verify as valid byte-observations"

# --- 4. each invalid fixture: verifier exit 1, output matches expected, ----
#        and fails for exactly its one stated reason -----------------------

for name in $INVALID_FIXTURES; do
    out="$TMPDIR_WORK/$name.out"
    set +e
    python3 "$VERIFIER" "$PACK/fixtures/invalid/$name.json" >"$out"
    rc=$?
    set -e
    if [ "$rc" -ne 1 ]; then
        printf 'ERROR: verifier exit %d on invalid fixture %s (expected 1)\n' "$rc" "$name" >&2
        exit 1
    fi
    diff -u "$PACK/expected/invalid/$name.txt" "$out"
done
pass "each invalid fixture is rejected for exactly its one stated reason"

# --- 5. witness-set aggregation: deterministic + order-independent ---------

set_a="$TMPDIR_WORK/witness_set.forward.out"
set_b="$TMPDIR_WORK/witness_set.reverse.out"
python3 "$VERIFIER" --witness-set \
    "$PACK/fixtures/valid/witness_a.json" \
    "$PACK/fixtures/valid/witness_b.json" \
    "$PACK/fixtures/valid/witness_c.json" \
    >"$set_a"
python3 "$VERIFIER" --witness-set \
    "$PACK/fixtures/valid/witness_c.json" \
    "$PACK/fixtures/valid/witness_b.json" \
    "$PACK/fixtures/valid/witness_a.json" \
    >"$set_b"
diff -u "$set_a" "$set_b"
diff -u "$PACK/expected/valid/witness_set.txt" "$set_a"
grep -q '^WITNESS-SET.*witness_count=3' "$set_a"
grep -q '^WITNESS-SET.*authority_effect=none' "$set_a"
pass "derived witness-set view is deterministic, order-independent, witness_count=3, authority_effect=none"

# --- 6. repo-level regression script still passes ---------------------------

python3 scripts/check_receipt_witness.py
pass "scripts/check_receipt_witness.py still passes"

# --- summary ---------------------------------------------------------------

printf 'PASS: receipt-witness pack v0.1 (%d checks)\n' "$step"
