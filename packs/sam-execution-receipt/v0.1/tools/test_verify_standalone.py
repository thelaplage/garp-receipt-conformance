#!/usr/bin/env python3
"""Parity + guard test for the SAM execution-receipt standalone verifier.

This test proves the properties the pack depends on:

1. ENVELOPE NON-DIVERGENCE. The standalone verifier vendors a copy of the
   canonical envelope-validation logic (tools/validate_srs_envelope.py) so it
   can ship as a single portable artifact. This test runs BOTH the vendored
   copy and the canonical in-repo validator over every fixture in this pack
   and asserts their envelope verdicts agree. If the vendored copy ever drifts
   from the canonical validator, this test fails.

2. STANDING-INJECTION GUARDRAIL. The five fixtures under fixtures/invalid/ all
   PASS the canonical envelope validator (proving that layer alone cannot
   catch verified/published/admitted/authority-grant injection for this
   body_kind) but FAIL the pack-local SAM standing-injection guardrail. This
   test asserts both halves of that claim.

3. DETERMINISTIC RECEIPT IDENTITY IS REORDERING-STABLE. A hand-reordered copy
   of a valid receipt's fields produces the identical canonical identity
   digest.

4. MUTATED BOUND DIGESTS INVALIDATE THE RECEIPT. Mutating
   canonical_arguments_digest or returned_payload_digest away from what the
   explicit input file declares makes the cryptographic-binding check fail --
   this is the acceptance-gate behavior: "argument mutation" / "returned-
   payload mutation" invalidate a mismatched receipt.

5. FULL ARC. Each of the four outcome fixtures (success / refused /
   transport_failure / contaminated_response) verifies end-to-end (exit 0);
   each of the five injection fixtures fails end-to-end (exit 1).

Standard library only. Run it directly:

    python3 packs/sam-execution-receipt/v0.1/tools/test_verify_standalone.py
"""

from __future__ import annotations

import copy
import json
import sys

sys.dont_write_bytecode = True

import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PACK_ROOT = TOOLS_DIR.parent
REPO_ROOT = PACK_ROOT.parent.parent.parent

VALID_NAMES = ("success", "refused", "transport_failure", "contaminated")
INVALID_NAMES = (
    "top_level_verified_true",
    "top_level_published_true",
    "body_admitted_true",
    "body_authority_grant",
    "body_evidence_support_injection",
)

VALID_FIXTURES = {
    name: PACK_ROOT / "fixtures" / "valid" / f"sam_execution_{name}.envelope.json"
    for name in VALID_NAMES
}
VALID_INPUTS = {
    name: PACK_ROOT / "input" / f"sam_execution_{name}.input.json"
    for name in VALID_NAMES
}
INVALID_FIXTURES = {
    name: PACK_ROOT / "fixtures" / "invalid" / f"{name}.json" for name in INVALID_NAMES
}

# This one is rejected by the CANONICAL envelope validator itself
# (TOP_LEVEL_BODY_VERDICT) -- the same drift class every other pack in this
# repo demonstrates -- unlike INVALID_FIXTURES above, which are all
# canonical-envelope-VALID and are rejected only by the pack-local SAM
# standing-injection guardrail.
CANONICAL_DRIFT_FIXTURES = {
    "top_level_status_verdict": PACK_ROOT
    / "fixtures"
    / "invalid"
    / "top_level_status_verdict.json",
}

SCHEMA = REPO_ROOT / "schemas" / "srs-envelope" / "v0.1.0" / "srs-envelope.schema.json"
MANIFEST = (
    REPO_ROOT / "schemas" / "srs-envelope" / "v0.1.0" / "srs-envelope.schema.manifest.json"
)
CANONICAL_VALIDATOR = REPO_ROOT / "tools" / "validate_srs_envelope.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - import plumbing
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


vs = _load("sam_verify_standalone", TOOLS_DIR / "verify_standalone.py")
canon = _load("validate_srs_envelope", CANONICAL_VALIDATOR)


_passed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global _passed
    if not condition:
        raise AssertionError(f"FAIL: {label}{(' — ' + detail) if detail else ''}")
    _passed += 1
    print(f"ok {_passed} - {label}")


def _canonical_codes(receipt_path: Path) -> list[str]:
    _manifest, schema, _digest = canon.load_canonical(MANIFEST, SCHEMA)
    return canon.validate_receipt(receipt_path, schema).codes


def _standalone_codes(receipt_path: Path) -> list[str]:
    schema = json.loads(SCHEMA.read_bytes())
    receipt = json.loads(receipt_path.read_bytes())
    return vs.validate_envelope(receipt, schema).codes


def reorder_deep(value):
    """Recursively reverse dict key order (content-preserving reordering)."""
    if isinstance(value, dict):
        return {k: reorder_deep(v) for k, v in reversed(list(value.items()))}
    if isinstance(value, list):
        return [reorder_deep(x) for x in value]
    return value


def main() -> int:
    # --- 1. ENVELOPE PARITY across every fixture in this pack ---------------
    all_fixtures = {**VALID_FIXTURES, **INVALID_FIXTURES, **CANONICAL_DRIFT_FIXTURES}
    for name, path in all_fixtures.items():
        canon_codes = _canonical_codes(path)
        standalone_codes = _standalone_codes(path)
        check(
            f"envelope parity: {name} (canonical={canon_codes} standalone={standalone_codes})",
            sorted(canon_codes) == sorted(standalone_codes),
        )

    # Valid outcomes AND the standing-injection fixtures alike are
    # envelope-valid SRS envelopes -- the injection fixtures are rejected at
    # the SAM-guardrail layer, not the envelope layer.
    for name, path in {**VALID_FIXTURES, **INVALID_FIXTURES}.items():
        codes = _canonical_codes(path)
        check(f"canonical validator accepts envelope shape: {name}", codes == [], f"codes={codes}")

    # The canonical-drift fixture is rejected by the envelope layer itself,
    # the same TOP_LEVEL_BODY_VERDICT class every other pack in this repo
    # demonstrates.
    for name, path in CANONICAL_DRIFT_FIXTURES.items():
        codes = _canonical_codes(path)
        check(
            f"canonical validator rejects drift fixture: {name}",
            "TOP_LEVEL_BODY_VERDICT" in codes,
            f"codes={codes}",
        )

    # --- 2. STANDING-INJECTION GUARDRAIL: valid fixtures pass, invalid fail -
    for name, path in VALID_FIXTURES.items():
        receipt = json.loads(path.read_bytes())
        result = vs.EnvelopeResult()
        vs.enforce_sam_guardrails(receipt, result)
        check(f"SAM guardrail accepts valid fixture: {name}", result.ok, f"codes={result.codes}")

    for name, path in INVALID_FIXTURES.items():
        receipt = json.loads(path.read_bytes())
        result = vs.EnvelopeResult()
        vs.enforce_sam_guardrails(receipt, result)
        check(
            f"SAM guardrail rejects injection fixture: {name}",
            not result.ok,
            f"codes={result.codes}",
        )

    # --- 3. DETERMINISTIC RECEIPT IDENTITY IS REORDERING-STABLE -------------
    base = json.loads(VALID_FIXTURES["success"].read_bytes())
    reordered = reorder_deep(base)
    id_original = vs.receipt_identity_digest(base)
    id_reordered = vs.receipt_identity_digest(reordered)
    check(
        "canonical receipt identity is invariant under field reordering",
        id_original == id_reordered,
        f"original={id_original} reordered={id_reordered}",
    )
    # Sanity: the reordered copy is a genuinely different Python dict ordering
    # (not a no-op), so the equality above is a real reordering-stability
    # claim, not a vacuous one.
    check(
        "reordering fixture actually changed on-disk key order (non-vacuous test)",
        list(base.keys()) != list(reordered.keys())
        or list(base["extensions"]["garp"]["body"].keys())
        != list(reordered["extensions"]["garp"]["body"].keys()),
    )

    # --- 4. MUTATED BOUND DIGESTS INVALIDATE THE RECEIPT ---------------------
    success_input = VALID_INPUTS["success"]

    mutated_args = copy.deepcopy(base)
    mutated_args["extensions"]["garp"]["body"]["canonical_arguments_digest"] = (
        "sha256:" + "0" * 64
    )
    ok, detail = vs.check_input_binding(mutated_args, success_input)
    check(
        "argument-digest mutation invalidates the receipt binding",
        not ok,
        detail,
    )

    mutated_payload = copy.deepcopy(base)
    mutated_payload["extensions"]["garp"]["body"]["returned_payload_digest"] = (
        "sha256:" + "1" * 64
    )
    ok, detail = vs.check_input_binding(mutated_payload, success_input)
    check(
        "returned-payload-digest mutation invalidates the receipt binding",
        not ok,
        detail,
    )

    ok, detail = vs.check_input_binding(base, success_input)
    check("unmutated receipt binding still verifies", ok, detail)

    # --- 5. FULL ARC: valid fixtures verify end-to-end, invalid fixtures fail
    for name, path in VALID_FIXTURES.items():
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = vs.main(
                [
                    "--receipt", str(path),
                    "--input", str(VALID_INPUTS[name]),
                    "--schema", str(SCHEMA),
                    "--manifest", str(MANIFEST),
                ]
            )
        check(f"full arc: {name} verifies end-to-end (exit 0)", rc == 0, f"exit={rc}")
        check(f"full arc: {name} report records VERIFIED", "Result: VERIFIED" in buf.getvalue())

    for name, path in {**INVALID_FIXTURES, **CANONICAL_DRIFT_FIXTURES}.items():
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = vs.main(
                [
                    "--receipt", str(path),
                    "--input", str(success_input),
                    "--schema", str(SCHEMA),
                    "--manifest", str(MANIFEST),
                ]
            )
        check(f"full arc: {name} fails end-to-end (exit 1)", rc == 1, f"exit={rc}")
        check(
            f"full arc: {name} report records NOT VERIFIED",
            "Result: NOT VERIFIED" in buf.getvalue(),
        )

    print(f"PASS: SAM execution-receipt standalone verifier parity + guard ({_passed} checks)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
