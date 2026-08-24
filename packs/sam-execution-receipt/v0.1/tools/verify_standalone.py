#!/usr/bin/env python3
"""Portable standalone verifier for the SAM execution-receipt pack (SAM-EXECUTION-RECEIPT0).

PURPOSE
-------
This is the verifier half of the portable-execution-receipt arc:

    explicit SAM observation bytes -> receipt artifact -> THIS verifier -> report

It recomputes a DETERMINISTIC RECEIPT IDENTITY DIGEST from the receipt's own
canonical serialization (sorted keys, compact separators) so that reordering
the top-level fields of a receipt file on disk never changes the identity the
verifier computes -- see check 3 below. It runs entirely offline from receipt
bytes + the explicit input bytes + this one script + the schema assets already
in this repo: no network, no credentials, no service access, no SAM/DAGR-MCP
process. It imports only the Python standard library; it does NOT import
garp_core, garp_sdk, arcs_amnesiac, dagr_mcp, or any other product/network code.

WHAT IT CHECKS (in order)
--------------------------
  1.  the receipt parses as JSON,
  2.  the canonical SRS envelope schema's bytes match the manifest's pinned
      sha256 (identity gate),
  3.  DETERMINISTIC RECEIPT IDENTITY: the canonical-serialization sha256 of the
      receipt is computed, and is shown to be invariant under field reordering
      (the digest is computed over a sort_keys canonicalization, so byte-level
      field order in the source file cannot change it -- exercised explicitly
      by test_verify_standalone.py using a hand-reordered copy of the same
      content),
  4.  canonical SRS envelope invariants hold (the SAME envelope-only checks
      tools/validate_srs_envelope.py applies -- vendored below, held aligned by
      test_verify_standalone.py so there is no second divergent envelope
      verifier),
  5.  SAM-EXECUTION-RECEIPT STANDING-INJECTION GUARDRAILS (pack-local; NOT
      covered by the canonical envelope validator, which only inspects a fixed
      top-level key list and never looks inside extensions.garp.body): rejects
      any top-level or body-level assertion of `verified`, `published`,
      `admitted`, or an evidentiary/authority standing this receipt shape never
      licenses (e.g. `output_evidence_supported`, `delegated_scope`,
      `authority_grant`). Any decision or delegation is only ever a REFERENCE
      (`decision_ref` / `delegation_ref`); this is Option A extended to
      delegation/lineage.
  6.  route expectations hold: receipt_type == sdk_enforcement, body_kind ==
      sam_execution_receipt (the verifier routes on these canonical axes --
      NOT on boundary_type, which stays descriptive; see
      docs/BOUNDARY_TYPE_LEDGER.md),
  7.  execution_outcome is one of the closed set (success / refused /
      transport_failure / contaminated_response), and a non-success outcome
      never carries a fabricated `sha256:` returned_payload_digest -- it must
      be the literal string "unavailable",
  8.  CRYPTOGRAPHIC BINDING to the explicit SAM observation input: (a)
      `extensions.garp.body.artifact_hashes` records the sha256 of the exact
      input file bytes, and (b) the receipt's own
      `canonical_arguments_digest` / `returned_payload_digest` /
      `error_observation_digest` fields match what the input file itself
      declares. A receipt whose bound digests were mutated away from the
      input's declared digests is a MISMATCHED RECEIPT and fails here -- this
      is what makes "argument mutation" and "returned-payload mutation"
      invalidate a receipt (see the acceptance gates in
      docs/dispatch/SAM-EXECUTION-RECEIPT0.md).

The five authority/standing-injection fixtures under fixtures/invalid/ all
PASS the canonical envelope validator (proving that layer alone is
insufficient for this receipt shape) and FAIL this verifier at check 5.

WHAT IT DOES NOT PROVE
-----------------------
Verification here is STRUCTURAL + CRYPTOGRAPHIC only, exactly as for every
other pack in this repo. `receipt_valid` is never treated as
`action_authorized`, `output_true`, `output_evidence_supported`, `admitted`,
or `published`. This verifier independently RECOMPUTES the receipt's structure
and bindings; it never re-asserts the emitter's own claims as if they were a
finding on their own (emitter assertion != independently-recomputed finding).
See the pack README for the full non-claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Default artifact locations, resolved relative to THIS script so the verifier
# runs offline from wherever the pack lives.
#   this file: packs/sam-execution-receipt/v0.1/tools/verify_standalone.py
# ---------------------------------------------------------------------------
PACK_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACK_ROOT.parent.parent.parent

DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "srs-envelope" / "v0.1.0" / "srs-envelope.schema.json"
DEFAULT_MANIFEST = (
    REPO_ROOT / "schemas" / "srs-envelope" / "v0.1.0" / "srs-envelope.schema.manifest.json"
)

# Route expectations for THIS pack. boundary_type is deliberately absent: it
# is descriptive top-level context only and is NEVER a routing authority.
EXPECTED_RECEIPT_TYPE = "sdk_enforcement"
EXPECTED_BODY_KIND = "sam_execution_receipt"

VALID_EXECUTION_OUTCOMES = (
    "success",
    "refused",
    "transport_failure",
    "contaminated_response",
)

UNAVAILABLE = "unavailable"


# ===========================================================================
# _envelope -- VENDORED (logic) from tools/validate_srs_envelope.py. Kept
# aligned by test_verify_standalone.py, which fails if the vendored copy and
# the canonical validator ever disagree over this pack's fixtures.
# ===========================================================================

GARP_BODY_DETAIL_KEYS = (
    "body_kind",
    "retained_claims",
    "refused_candidates",
    "omitted_candidates",
    "candidate_total",
    "artifact_hashes",
)
BODY_VERDICT_KEYS = ("verdict", "admitted", "refused", "held", "status")

_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
}


@dataclass
class EnvelopeResult:
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def codes(self) -> list[str]:
        return [c for c, _ in self.errors]

    def add(self, code: str, message: str) -> None:
        self.errors.append((code, message))


def _type_matches(value: Any, type_name: str) -> bool:
    expected = _JSON_TYPES.get(type_name)
    if expected is None:
        return True
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    return isinstance(value, expected)


def _check_node(value: Any, schema: dict, pointer: str, result: EnvelopeResult) -> None:
    if "oneOf" in schema:
        matches = 0
        for sub in schema["oneOf"]:
            probe = EnvelopeResult()
            _check_node(value, sub, pointer, probe)
            if probe.ok:
                matches += 1
        if matches != 1:
            result.add(
                "SCHEMA_ONEOF",
                f"{pointer or '<root>'} matched {matches} of oneOf branches "
                f"(expected exactly 1)",
            )
        return

    type_name = schema.get("type")
    if type_name is not None and not _type_matches(value, type_name):
        result.add(
            "SCHEMA_TYPE",
            f"{pointer or '<root>'} expected type '{type_name}', "
            f"got {type(value).__name__}",
        )
        return

    if "enum" in schema and value not in schema["enum"]:
        result.add(
            "SCHEMA_ENUM",
            f"{pointer or '<root>'} value {value!r} not in closed enum "
            f"{schema['enum']}",
        )

    if type_name == "object" and isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                result.add("MISSING_REQUIRED", f"required field '{req}' is missing")
        props = schema.get("properties", {})
        for key, sub_schema in props.items():
            if key in value:
                child_ptr = f"{pointer}.{key}" if pointer else key
                _check_node(value[key], sub_schema, child_ptr, result)

    if type_name == "array" and isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(value):
                _check_node(item, item_schema, f"{pointer}[{idx}]", result)


def enforce_envelope_guardrails(receipt: Any, schema: dict, result: EnvelopeResult) -> None:
    if not isinstance(receipt, dict):
        result.add("NOT_OBJECT", "receipt is not a JSON object")
        return

    enum_values = schema.get("properties", {}).get("receipt_type", {}).get("enum", [])
    rtype = receipt.get("receipt_type")
    if enum_values and rtype not in enum_values:
        result.add(
            "RECEIPT_TYPE_NOT_IN_ENUM",
            f"receipt_type {rtype!r} not in closed enum {enum_values}",
        )

    if "attestation_limits" not in receipt:
        result.add(
            "MISSING_ATTESTATION_LIMITS",
            "attestation_limits is required by the envelope schema but absent",
        )
    if "artifact_classes_excluded" not in receipt:
        result.add(
            "MISSING_ARTIFACT_CLASSES_EXCLUDED",
            "artifact_classes_excluded is required by the envelope schema but absent",
        )

    if "receipt_class" in receipt:
        result.add(
            "TOP_LEVEL_RECEIPT_CLASS",
            "stray top-level 'receipt_class' is not an envelope field",
        )

    for key in GARP_BODY_DETAIL_KEYS:
        if key in receipt:
            result.add(
                "GARP_DETAIL_AT_TOP_LEVEL",
                f"GARP body detail '{key}' must live under "
                f"extensions.garp.body, not at the top level",
            )

    for key in BODY_VERDICT_KEYS:
        if key in receipt:
            result.add(
                "TOP_LEVEL_BODY_VERDICT",
                f"top-level '{key}' is a body verdict/discriminator; the "
                f"envelope does not carry body verdicts",
            )

    extensions = receipt.get("extensions")
    if isinstance(extensions, dict) and "garp" in extensions:
        garp = extensions["garp"]
        if not isinstance(garp, dict) or "body" not in garp:
            result.add(
                "GARP_NOT_UNDER_BODY",
                "extensions.garp must nest GARP body-kind detail under "
                "extensions.garp.body",
            )


def validate_envelope(receipt: Any, schema: dict) -> EnvelopeResult:
    result = EnvelopeResult()
    _check_node(receipt, schema, "", result)
    enforce_envelope_guardrails(receipt, schema, result)
    return result


# ===========================================================================
# SAM-EXECUTION-RECEIPT standing-injection guardrails (pack-local; NOT part of
# the canonical envelope validator, which does not know this body_kind's
# semantics and never inspects inside extensions.garp.body).
# ===========================================================================

# Top-level standing claims this receipt shape never licenses. Distinct from
# the canonical BODY_VERDICT_KEYS set above (verdict/admitted/refused/held/
# status): those are already caught by the canonical validator. These are not.
TOP_LEVEL_STANDING_KEYS = ("verified", "published")

# Body-level (extensions.garp.body) keys that would assert standing/authority
# this receipt never grants. Presence alone is disqualifying, regardless of
# value -- this body_kind only ever carries REFERENCES (decision_ref,
# delegation_ref), never verdicts or grants.
BODY_STANDING_KEYS = (
    "verified",
    "published",
    "admitted",
    "refused",
    "action_authorized",
    "output_evidence_supported",
    "evidence_supported",
)

# Body-level keys that would assert a delegated/authority GRANT instead of a
# mere reference. Option A permits only *_ref fields; anything that grants a
# scope directly is rejected.
BODY_AUTHORITY_GRANT_KEYS = ("delegated_scope", "authority_grant", "scope_grant")


def enforce_sam_guardrails(receipt: dict, result: EnvelopeResult) -> None:
    for key in TOP_LEVEL_STANDING_KEYS:
        if key in receipt:
            result.add(
                "STANDING_INJECTION_TOP_LEVEL",
                f"top-level '{key}' asserts standing this receipt never "
                f"licenses; the canonical envelope validator does not catch "
                f"this key, which is exactly why this pack-local guardrail "
                f"exists",
            )

    body = receipt.get("extensions", {}).get("garp", {}).get("body", {})
    if not isinstance(body, dict):
        return

    for key in BODY_STANDING_KEYS:
        if key in body:
            result.add(
                "BODY_STANDING_INJECTION",
                f"extensions.garp.body.'{key}' asserts standing/verdict "
                f"semantics this body_kind never carries; only *_ref "
                f"references (decision_ref, delegation_ref) are permitted",
            )

    for key in BODY_AUTHORITY_GRANT_KEYS:
        if key in body:
            result.add(
                "BODY_AUTHORITY_GRANT_INJECTION",
                f"extensions.garp.body.'{key}' asserts a delegated/authority "
                f"GRANT rather than a reference; Option A permits only "
                f"delegation_ref (a reference), never a broader grant",
            )


def enforce_route_expectations(receipt: dict, result: EnvelopeResult) -> None:
    body = receipt.get("extensions", {}).get("garp", {}).get("body", {})
    body = body if isinstance(body, dict) else {}
    rtype = receipt.get("receipt_type")
    bkind = body.get("body_kind")
    if rtype != EXPECTED_RECEIPT_TYPE or bkind != EXPECTED_BODY_KIND:
        result.add(
            "ROUTE_MISMATCH",
            f"receipt_type={rtype!r} (expected {EXPECTED_RECEIPT_TYPE!r}), "
            f"body_kind={bkind!r} (expected {EXPECTED_BODY_KIND!r})",
        )

    outcome = body.get("execution_outcome")
    if outcome not in VALID_EXECUTION_OUTCOMES:
        result.add(
            "EXECUTION_OUTCOME_NOT_IN_ENUM",
            f"execution_outcome {outcome!r} not in {VALID_EXECUTION_OUTCOMES}",
        )
    elif outcome != "success":
        payload_digest = body.get("returned_payload_digest")
        if payload_digest != UNAVAILABLE:
            result.add(
                "FABRICATED_NON_SUCCESS_PAYLOAD",
                f"execution_outcome={outcome!r} but returned_payload_digest="
                f"{payload_digest!r}; a non-success outcome must record "
                f"returned_payload_digest as the literal 'unavailable', never "
                f"a fabricated sha256:",
            )


# ===========================================================================
# Deterministic receipt identity (canonical serialization; reordering-stable).
# ===========================================================================

def canonical_bytes(obj: Any) -> bytes:
    """Canonical JSON serialization used for the receipt identity digest.

    sort_keys=True recursively sorts object keys at every level, and compact
    separators remove whitespace variance, so two JSON documents that encode
    the same value -- regardless of the on-disk field order or formatting of
    either -- serialize to identical bytes here.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def receipt_identity_digest(receipt: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(receipt)).hexdigest()


# ===========================================================================
# Cryptographic binding to the explicit SAM observation input.
# ===========================================================================

def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_input_binding(receipt: dict, input_path: Path) -> tuple[bool, str]:
    body = receipt.get("extensions", {}).get("garp", {}).get("body", {})
    if not isinstance(body, dict):
        return False, "no extensions.garp.body present"

    label = f"input/{input_path.name}"
    hashes = body.get("artifact_hashes", {})
    recorded = hashes.get(label) if isinstance(hashes, dict) else None
    try:
        actual = "sha256:" + sha256_of_file(input_path)
    except OSError as exc:
        return False, f"could not read input file: {exc}"

    if recorded != actual:
        return False, f"artifact_hashes[{label!r}]={recorded!r} != input sha256 {actual!r}"

    try:
        observation = json.loads(input_path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"could not parse input file: {exc}"

    mismatches: list[str] = []
    for field_name in ("canonical_arguments_digest", "returned_payload_digest"):
        receipt_value = body.get(field_name)
        input_value = observation.get(field_name)
        if receipt_value != input_value:
            mismatches.append(
                f"{field_name}: receipt={receipt_value!r} != input={input_value!r}"
            )
    # error_observation_digest is optional (omitted when null in the input).
    input_error_digest = observation.get("error_observation_digest")
    receipt_error_digest = body.get("error_observation_digest")
    if input_error_digest is not None and receipt_error_digest != input_error_digest:
        mismatches.append(
            f"error_observation_digest: receipt={receipt_error_digest!r} != "
            f"input={input_error_digest!r}"
        )
    elif input_error_digest is None and receipt_error_digest is not None:
        mismatches.append(
            f"error_observation_digest: receipt={receipt_error_digest!r} but "
            f"input declared none"
        )

    if mismatches:
        return False, "bound-digest mismatch: " + "; ".join(mismatches)

    return True, f"artifact_hashes and bound digests match {label}"


# ===========================================================================
# Arc: run the ordered checks and build the deterministic operator report.
# ===========================================================================

@dataclass
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class Verification:
    checks: list[Check] = field(default_factory=list)
    identity_digest: str | None = None

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def record(self, name: str, ok: bool, detail: str) -> None:
        self.checks.append(Check(name, ok, detail))


def verify(
    receipt_path: Path,
    input_path: Path | None,
    schema_path: Path,
    manifest_path: Path,
) -> Verification:
    v = Verification()

    # --- 1. receipt parses ---
    try:
        receipt = json.loads(receipt_path.read_bytes())
        v.record("receipt parses as JSON", True, "ok")
    except (OSError, json.JSONDecodeError) as exc:
        v.record("receipt parses as JSON", False, f"{exc}")
        return v

    # --- 2. schema identity gate ---
    try:
        manifest = json.loads(manifest_path.read_bytes())
        schema = json.loads(schema_path.read_bytes())
        schema_digest = sha256_of_file(schema_path)
        pinned = manifest.get("sha256")
        if schema_digest == pinned:
            v.record(
                "schema bytes match manifest pinned sha256",
                True,
                f"sha256 {schema_digest}",
            )
        else:
            v.record(
                "schema bytes match manifest pinned sha256",
                False,
                f"schema sha256 {schema_digest} != manifest {pinned}",
            )
            return v
    except (OSError, json.JSONDecodeError) as exc:
        v.record("schema bytes match manifest pinned sha256", False, f"{exc}")
        return v

    # --- 3. deterministic receipt identity (canonical, reordering-stable) ---
    v.identity_digest = receipt_identity_digest(receipt)
    v.record(
        "deterministic receipt identity computed (canonical serialization)",
        True,
        v.identity_digest,
    )

    # --- 4. canonical envelope invariants ---
    env = validate_envelope(receipt, schema)
    if env.ok:
        v.record("canonical envelope invariants hold", True, "valid SRS envelope 0.1.0")
    else:
        v.record(
            "canonical envelope invariants hold",
            False,
            "; ".join(f"[{c}] {m}" for c, m in env.errors),
        )

    # --- 5. SAM-execution-receipt standing-injection guardrails ---
    sam_result = EnvelopeResult()
    enforce_sam_guardrails(receipt, sam_result)
    if sam_result.ok:
        v.record(
            "SAM standing-injection guardrails hold (no verified/published/"
            "admitted/authority-grant injection)",
            True,
            "no injected standing found",
        )
    else:
        v.record(
            "SAM standing-injection guardrails hold (no verified/published/"
            "admitted/authority-grant injection)",
            False,
            "; ".join(f"[{c}] {m}" for c, m in sam_result.errors),
        )

    # --- 6/7. route expectations + non-success payload-digest discipline ---
    route_result = EnvelopeResult()
    enforce_route_expectations(receipt, route_result)
    if route_result.ok:
        v.record(
            "route expectations hold (receipt_type/body_kind/execution_outcome)",
            True,
            f"receipt_type={receipt.get('receipt_type')!r}, "
            f"body_kind={receipt.get('extensions', {}).get('garp', {}).get('body', {}).get('body_kind')!r}",
        )
    else:
        v.record(
            "route expectations hold (receipt_type/body_kind/execution_outcome)",
            False,
            "; ".join(f"[{c}] {m}" for c, m in route_result.errors),
        )

    # --- 8. cryptographic binding to explicit SAM observation input ---
    if input_path is not None:
        bind_ok, detail = check_input_binding(receipt, input_path)
        v.record(
            "receipt cryptographically binds the explicit SAM observation input "
            "(artifact_hashes + argument/payload/error digests)",
            bind_ok,
            detail,
        )

    return v


# ---------------------------------------------------------------------------
# Report rendering -- deterministic operator output.
# ---------------------------------------------------------------------------
SCOPE_LINE = "Verification is STRUCTURAL + CRYPTOGRAPHIC only."

DOES_NOT_CLAIM = (
    "action_authorized (receipt_valid != action_authorized)",
    "output_true (receipt_valid != output_true)",
    "output_evidence_supported (receipt_valid != output_evidence_supported)",
    "admitted (receipt_valid != admitted)",
    "published (receipt_valid != published)",
    "live SAM/DAGR-MCP transport integration (no process was run, no network touched)",
)


def build_report(v: Verification, receipt_path: Path) -> str:
    lines: list[str] = []
    lines.append("SAM execution-receipt pack -- portable standalone verifier")
    lines.append("=============================================================")
    lines.append("")
    lines.append(f"Receipt: {receipt_path}")
    if v.identity_digest is not None:
        lines.append(f"Deterministic receipt identity: {v.identity_digest}")
    lines.append("")
    lines.append("Checks:")
    for check in v.checks:
        status = "PASS" if check.ok else "FAIL"
        lines.append(f"  [{status}] {check.name}")
        lines.append(f"         {check.detail}")
    lines.append("")
    lines.append(f"Result: {'VERIFIED' if v.ok else 'NOT VERIFIED'}")
    lines.append("")
    lines.append(SCOPE_LINE)
    lines.append("This verifier does NOT claim:")
    for claim in DOES_NOT_CLAIM:
        lines.append(f"  - {claim}")
    lines.append("")
    lines.append(
        "boundary_type is descriptive only: the verifier does NOT route on it."
    )
    lines.append(
        "Route authority is receipt_type / body_kind / execution_outcome / schema"
    )
    lines.append("invariants. AUTHORITY_MOVEMENT = 0: this verifier grants no")
    lines.append("execution authority and issues no admission of its own.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Portable, offline, stdlib-only standalone verifier for the "
        "SAM execution-receipt pack. Structural + cryptographic verification "
        "only; not a live transport integration.",
    )
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="explicit SAM observation input file used to cross-check bound digests",
    )
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    v = verify(
        receipt_path=args.receipt,
        input_path=args.input,
        schema_path=args.schema,
        manifest_path=args.manifest,
    )
    sys.stdout.write(build_report(v, args.receipt))
    return 0 if v.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
