#!/usr/bin/env python3
"""Portable standalone verifier for the Bedrock/OpenAI explicit-file pack.

PURPOSE
-------
This is the *prospect-runnable* half of the Bedrock/OpenAI custody/audit arc:

    explicit input bytes -> receipt artifact -> THIS verifier -> deterministic report

The claim it proves is portability: a prospect can run it offline from
**receipt bytes + this one script + the schema assets already in this repo/pack**
— with **no garp-local checkout, no install, no network, no credentials, no env
vars, no API calls, no scanner, and no service access**. It imports only the
Python standard library; it does NOT import garp_core, garp_sdk, arcs_amnesiac,
or any other Vega/GARP product code.

WHAT IT CHECKS
--------------
For the receipt under verification it asserts, in order:

  1. the receipt parses as JSON,
  2. the canonical schema's bytes match the manifest's pinned sha256 (identity
     gate — a receipt is only judged against schema bytes of known identity),
  3. schema/envelope invariants hold (the same envelope-only checks the
     canonical in-repo validator, ``tools/validate_srs_envelope.py``, applies),
  4. receipt_type / body_kind route expectations hold (the verifier routes on
     these canonical axes — NOT on ``boundary_type``),
  5. ``extensions.garp.body.artifact_hashes`` records the sha256 of the exact
     explicit input bytes (cryptographic input-byte binding),
  6. the rendered plain-language reading of the receipt matches the expected
     reading byte-for-byte (a bundled, deterministic renderer).

The drift fixture (a receipt that hoists a decision to a top-level ``status``
verdict) fails at step 3, exactly as it does under the canonical validator.

NON-DIVERGENCE
--------------
The envelope-validation logic in the ``_envelope`` section below is VENDORED
from ``tools/validate_srs_envelope.py`` so that this script is a single
self-contained portable artifact. It is the SAME logic, not a different one:
``packs/bedrock-openai-audit/v0.1/tools/test_verify_standalone.py`` is a parity
guard that runs both this verifier and the canonical validator over the pack's
valid and invalid fixtures and fails if their envelope verdicts ever disagree.
Keep the two in sync; the parity test is what proves they have not diverged.

WHAT IT DOES NOT PROVE
----------------------
Verification here is **structural + cryptographic only**. It does NOT establish
truth, admission, compliance certification, live AWS/OpenAI/Bedrock integration,
model-output verification, or production authorization. See the report footer
and the pack README for the full non-claim.
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
# runs offline from wherever the pack lives — no repo-root cwd assumption, no
# garp-local checkout. All are overridable on the command line.
#   this file: packs/bedrock-openai-audit/v0.1/tools/verify_standalone.py
# ---------------------------------------------------------------------------
PACK_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACK_ROOT.parent.parent.parent

DEFAULT_RECEIPT = PACK_ROOT / "fixtures" / "valid" / "bedrock_openai_audit.envelope.json"
DEFAULT_INPUT = PACK_ROOT / "input" / "bedrock_openai_audit.input.json"
DEFAULT_READING = PACK_ROOT / "expected" / "valid" / "bedrock_openai_audit.reading.txt"
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "srs-envelope" / "v0.1.0" / "srs-envelope.schema.json"
DEFAULT_MANIFEST = (
    REPO_ROOT / "schemas" / "srs-envelope" / "v0.1.0" / "srs-envelope.schema.manifest.json"
)

# Route expectations for THIS pack. These are the canonical routing axes the
# verifier branches on. boundary_type is deliberately absent: it is descriptive
# top-level context only and is NEVER a routing authority here. See
# docs/BOUNDARY_TYPE_LEDGER.md.
EXPECTED_RECEIPT_TYPE = "provenance"
EXPECTED_BODY_KIND = "bedrock_openai_custody_audit"

# The logical input artifact name used as the artifact_hashes key.
INPUT_ARTIFACT_LABEL = "input/bedrock_openai_audit.input.json"


# ===========================================================================
# _envelope — VENDORED VERBATIM (logic) from tools/validate_srs_envelope.py.
# Single source of truth in spirit: the parity test test_verify_standalone.py
# fails if these checks ever disagree with the canonical validator. Do not let
# this drift.
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
    """Outcome of envelope validation: a list of (code, message) error pairs."""

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
    """Run the schema-subset check and the envelope guardrails (vendored)."""
    result = EnvelopeResult()
    _check_node(receipt, schema, "", result)
    enforce_envelope_guardrails(receipt, schema, result)
    return result


# ===========================================================================
# Bundled plain-language renderer.
# Produces a deterministic, human-readable reading of an SRS envelope receipt
# from the receipt's own fields. The JSON receipt remains the authoritative
# artifact; this reading is the byte-for-byte comparison target for check 6.
# ===========================================================================

def _body_of(receipt: dict) -> dict:
    body = receipt.get("extensions", {}).get("garp", {}).get("body", {})
    return body if isinstance(body, dict) else {}


def render_reading(receipt: dict) -> str:
    """Render the plain-language reading of a receipt. Deterministic."""
    body = _body_of(receipt)
    lines: list[str] = []
    lines.append("SRS envelope receipt — plain-language reading")
    lines.append("=============================================")
    lines.append("")
    lines.append("Envelope:")
    lines.append(f"  receipt_id        {receipt.get('receipt_id', '')}")
    lines.append(f"  receipt_type      {receipt.get('receipt_type', '')}")
    lines.append(f"  receipt_version   {receipt.get('receipt_version', '')}")
    lines.append(f"  protocol_binding  {receipt.get('protocol_binding', '')}")
    lines.append(f"  subject_ref       {receipt.get('subject_ref', '')}")
    lines.append(f"  issued_at         {receipt.get('issued_at', '')}")
    lines.append(
        f"  boundary_type     {receipt.get('boundary_type', '')}"
        "  (descriptive context only; not a routing authority)"
    )
    lines.append("")
    lines.append("GARP body (extensions.garp.body):")
    lines.append(f"  body_kind         {body.get('body_kind', '')}")
    lines.append(f"  gateway_ref       {body.get('gateway_ref', '')}")
    lines.append(f"  session_ref       {body.get('session_ref', '')}")
    providers = body.get("providers", [])
    if isinstance(providers, list):
        lines.append(f"  providers         {', '.join(str(p) for p in providers)}")
    lines.append(f"  event_count       {body.get('event_count', '')}")
    if "decision_ref" in body:
        lines.append(
            f"  decision_ref      {body['decision_ref']}"
        )
        lines.append("                    (Option A reference; not a verdict)")
    lines.append("")
    lines.append("Recorded model-invocation custody events (digest-only):")
    events = body.get("events", [])
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            digest = event.get("prompt_digest")
            digest_label = "prompt"
            if digest is None:
                digest = event.get("output_digest")
                digest_label = "output"
            digest_text = f"{digest_label} {digest}" if digest is not None else ""
            lines.append(
                f"  seq {event.get('seq', '')}  "
                f"{str(event.get('kind', '')):<20} "
                f"{str(event.get('provider', '')):<8} "
                f"{str(event.get('model_ref', '')):<24} "
                f"{str(event.get('custody', '')):<16} "
                f"{digest_text}".rstrip()
            )
    lines.append("")
    lines.append("Input-byte binding (extensions.garp.body.artifact_hashes):")
    hashes = body.get("artifact_hashes", {})
    if isinstance(hashes, dict):
        for name in sorted(hashes):
            lines.append(f"  {name}  {hashes[name]}")
    lines.append("")
    lines.append("Attestation limits (carried inside the receipt):")
    for limit in receipt.get("attestation_limits", []):
        lines.append(f"  - {limit}")
    return "\n".join(lines) + "\n"


# ===========================================================================
# Arc: run the ordered checks and build the deterministic operator report.
# ===========================================================================

@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class Verification:
    checks: list[Check] = field(default_factory=list)
    reading: str | None = None

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def record(self, name: str, ok: bool, detail: str) -> None:
        self.checks.append(Check(name, ok, detail))


def verify(
    receipt_path: Path,
    input_path: Path,
    schema_path: Path,
    manifest_path: Path,
    reading_path: Path | None,
) -> Verification:
    v = Verification()

    # --- 1. receipt parses ---
    try:
        receipt = json.loads(receipt_path.read_bytes())
        v.record("receipt parses as JSON", True, "ok")
    except (OSError, json.JSONDecodeError) as exc:
        v.record("receipt parses as JSON", False, f"{exc}")
        return v

    # --- 2. schema identity gate (schema bytes == manifest pinned sha256) ---
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

    # --- 3. schema/envelope invariants (vendored canonical checks) ---
    env = validate_envelope(receipt, schema)
    if env.ok:
        v.record("schema/envelope invariants hold", True, "valid SRS envelope 0.1.0")
    else:
        detail = "; ".join(f"[{c}] {m}" for c, m in env.errors)
        v.record("schema/envelope invariants hold", False, detail)

    # --- 4. receipt_type / body_kind route expectations ---
    body = _body_of(receipt)
    rtype = receipt.get("receipt_type")
    bkind = body.get("body_kind")
    route_ok = rtype == EXPECTED_RECEIPT_TYPE and bkind == EXPECTED_BODY_KIND
    v.record(
        "receipt_type / body_kind route expectations hold",
        route_ok,
        f"receipt_type={rtype!r} (expected {EXPECTED_RECEIPT_TYPE!r}), "
        f"body_kind={bkind!r} (expected {EXPECTED_BODY_KIND!r}); "
        f"boundary_type={receipt.get('boundary_type')!r} is NOT routed on",
    )

    # --- 5. artifact_hashes input sha256 matches the explicit input bytes ---
    try:
        actual = "sha256:" + sha256_of_file(input_path)
        hashes = body.get("artifact_hashes", {})
        recorded = hashes.get(INPUT_ARTIFACT_LABEL) if isinstance(hashes, dict) else None
        bind_ok = recorded is not None and recorded == actual
        if bind_ok:
            detail = f"{INPUT_ARTIFACT_LABEL} {actual}"
        elif recorded is None:
            detail = f"no artifact_hashes entry for {INPUT_ARTIFACT_LABEL}"
        else:
            detail = f"recorded {recorded} != input {actual}"
        v.record(
            "artifact_hashes input sha256 matches explicit input bytes",
            bind_ok,
            detail,
        )
    except OSError as exc:
        v.record(
            "artifact_hashes input sha256 matches explicit input bytes",
            False,
            f"{exc}",
        )

    # --- 6. rendered plain-language reading matches expected byte-for-byte ---
    v.reading = render_reading(receipt)
    if reading_path is not None:
        try:
            expected_reading = reading_path.read_text(encoding="utf-8")
            reading_ok = v.reading == expected_reading
            v.record(
                "rendered plain-language reading matches expected (byte-for-byte)",
                reading_ok,
                "matches expected reading"
                if reading_ok
                else "rendered reading differs from expected reading",
            )
        except OSError as exc:
            v.record(
                "rendered plain-language reading matches expected (byte-for-byte)",
                False,
                f"{exc}",
            )

    return v


# ---------------------------------------------------------------------------
# Report rendering — deterministic operator output. No wall clock, no absolute
# paths, no randomness: identical input -> identical bytes.
# ---------------------------------------------------------------------------
SCOPE_LINE = "Verification is STRUCTURAL + CRYPTOGRAPHIC only."

DOES_NOT_CLAIM = (
    "truth of any recorded event",
    "admission",
    "compliance certification",
    "live AWS / OpenAI / Bedrock integration (no API was called)",
    "model-output verification (no model output is verified)",
    "production authorization",
)


def build_report(v: Verification) -> str:
    lines: list[str] = []
    lines.append("Bedrock/OpenAI explicit-file pack — portable standalone verifier")
    lines.append("================================================================")
    lines.append("")
    lines.append("Arc: explicit input bytes -> receipt artifact -> standalone verifier")
    lines.append("     -> this report. Offline; stdlib only; no garp-local checkout, no")
    lines.append("     install, no network, no credentials, no service access.")
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
        "Route authority is receipt_type / body_kind / schema invariants. The"
    )
    lines.append(
        "open-string boundary_type values are recorded in docs/BOUNDARY_TYPE_LEDGER.md."
    )
    if v.reading is not None:
        lines.append("")
        lines.append("-" * 64)
        lines.append("")
        lines.append(v.reading.rstrip("\n"))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Portable, offline, stdlib-only standalone verifier for the "
        "Bedrock/OpenAI explicit-file custody/audit pack. Structural + "
        "cryptographic verification only; not a live integration.",
    )
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--reading",
        type=Path,
        default=DEFAULT_READING,
        help="expected plain-language reading file for the byte-for-byte check",
    )
    parser.add_argument(
        "--no-reading-check",
        action="store_true",
        help="skip the expected-reading comparison (still renders the reading)",
    )
    parser.add_argument(
        "--emit",
        choices=("report", "reading"),
        default="report",
        help="emit the full operator report (default) or only the rendered reading",
    )
    args = parser.parse_args(argv)

    if args.emit == "reading":
        # Render-only mode: used to (re)generate the expected reading asset.
        try:
            receipt = json.loads(args.receipt.read_bytes())
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FATAL: could not load receipt: {exc}", file=sys.stderr)
            return 2
        sys.stdout.write(render_reading(receipt))
        return 0

    reading_path = None if args.no_reading_check else args.reading
    v = verify(
        receipt_path=args.receipt,
        input_path=args.input,
        schema_path=args.schema,
        manifest_path=args.manifest,
        reading_path=reading_path,
    )
    sys.stdout.write(build_report(v))
    return 0 if v.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
