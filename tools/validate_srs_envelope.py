#!/usr/bin/env python3
"""Standalone ARCS SRS *envelope* conformance validator.

This validator proves ARCS SRS ENVELOPE conformance only. It does NOT prove
GARP body-kind conformance, does NOT bless any GARP body semantics, and does
NOT assert truth, admission, custody, or public-surface eligibility.

It is intentionally dependency-light: it imports only the Python standard
library. It does NOT import garp_sdk, arcs_amnesiac, garp_core, or any other
Vega/GARP product code, and it does NOT edit the canonical schema.

What it does:
  1. Loads the canonical manifest and the canonical schema.
  2. Computes the schema file's sha256 and fails hard if it does not equal the
     manifest's recorded sha256 (the pinned identity digest).
  3. Validates a receipt against the envelope schema (a small built-in subset
     check covering the constructs this schema uses: type / required / enum /
     items / oneOf / properties).
  4. Enforces envelope-only guardrails on top of schema validation:
       - receipt_type must be in the closed enum
       - all required envelope fields present
       - attestation_limits present (required by the schema)
       - artifact_classes_excluded present (required by the schema)
       - GARP detail only under extensions.garp.body
       - no top-level receipt_class
       - no undefined top-level discriminator (e.g. top-level body_kind)
       - no top-level verdict / admitted / refused / held / status used as a
         body-verdict discriminator

Pinning note: consumers pin to published_version + sha256, never to a repo
path. This pack is built against pre-release 0.1.0, which may break before 1.0.
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
# Canonical artifact locations (relative to the repo root that contains this
# file under tools/). Override with --manifest / --schema if needed.
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = (
    REPO_ROOT
    / "schemas"
    / "srs-envelope"
    / "v0.1.0"
    / "srs-envelope.schema.manifest.json"
)
DEFAULT_SCHEMA = (
    REPO_ROOT / "schemas" / "srs-envelope" / "v0.1.0" / "srs-envelope.schema.json"
)

# Keys that carry GARP body-kind *detail*. They are legitimate only nested
# under extensions.garp.body; at the top level they leak body semantics into
# the envelope and are rejected.
GARP_BODY_DETAIL_KEYS = (
    "body_kind",
    "retained_claims",
    "refused_candidates",
    "omitted_candidates",
    "candidate_total",
    "artifact_hashes",
)

# Top-level keys that would smuggle a body verdict / discriminator into the
# envelope. The envelope never carries a body verdict.
BODY_VERDICT_KEYS = ("verdict", "admitted", "refused", "held", "status")


@dataclass
class Result:
    """Outcome of validating a single receipt.

    `errors` is a list of (code, message) pairs. `code` is a stable,
    machine-checkable token so self-tests can assert *why* a fixture failed.
    """

    path: str
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def codes(self) -> list[str]:
        return [c for c, _ in self.errors]

    def add(self, code: str, message: str) -> None:
        self.errors.append((code, message))


class SchemaHashMismatch(Exception):
    """Raised when the schema bytes do not match the manifest's pinned sha256."""


# ---------------------------------------------------------------------------
# Loading & identity verification
# ---------------------------------------------------------------------------
def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_schema_hash(schema_path: Path, manifest: dict) -> str:
    """Compute the schema file's sha256 and assert it equals the manifest's.

    Returns the computed digest on success; raises SchemaHashMismatch on
    failure. This is the identity gate: a receipt is only validated against a
    schema whose bytes match the pinned digest.
    """
    actual = sha256_of_file(schema_path)
    expected = manifest.get("sha256")
    if actual != expected:
        raise SchemaHashMismatch(
            f"schema sha256 {actual} != manifest sha256 {expected} "
            f"(schema={schema_path})"
        )
    return actual


# ---------------------------------------------------------------------------
# Minimal JSON Schema subset check (no third-party dependency).
# Supports only the constructs the envelope schema actually uses.
# ---------------------------------------------------------------------------
_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
}


def _type_matches(value: Any, type_name: str) -> bool:
    expected = _JSON_TYPES.get(type_name)
    if expected is None:
        return True  # unknown type keyword: do not block
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    return isinstance(value, expected)


def _check_node(value: Any, schema: dict, pointer: str, result: Result) -> None:
    """Validate one value against a schema node, recording errors in result."""
    if "oneOf" in schema:
        matches = 0
        for sub in schema["oneOf"]:
            probe = Result(result.path)
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
                result.add(
                    "MISSING_REQUIRED",
                    f"required field '{req}' is missing",
                )
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


def validate_against_schema(receipt: Any, schema: dict, result: Result) -> None:
    _check_node(receipt, schema, "", result)


# ---------------------------------------------------------------------------
# Envelope-only guardrails (layered on top of schema validation)
# ---------------------------------------------------------------------------
def enforce_envelope_guardrails(receipt: Any, schema: dict, result: Result) -> None:
    if not isinstance(receipt, dict):
        result.add("NOT_OBJECT", "receipt is not a JSON object")
        return

    # receipt_type must be in the closed enum (explicit guardrail; the schema
    # check above also covers this, but we assert it independently here so the
    # envelope contract does not silently depend on schema enforcement).
    enum_values = (
        schema.get("properties", {}).get("receipt_type", {}).get("enum", [])
    )
    rtype = receipt.get("receipt_type")
    if enum_values and rtype not in enum_values:
        result.add(
            "RECEIPT_TYPE_NOT_IN_ENUM",
            f"receipt_type {rtype!r} not in closed enum {enum_values}",
        )

    # attestation_limits / artifact_classes_excluded are required by the schema;
    # call them out with envelope-specific codes for clear failure reasons.
    if "attestation_limits" not in receipt:
        result.add(
            "MISSING_ATTESTATION_LIMITS",
            "attestation_limits is required by the envelope schema but absent",
        )
    if "artifact_classes_excluded" not in receipt:
        result.add(
            "MISSING_ARTIFACT_CLASSES_EXCLUDED",
            "artifact_classes_excluded is required by the envelope schema "
            "but absent",
        )

    # No top-level receipt_class.
    if "receipt_class" in receipt:
        result.add(
            "TOP_LEVEL_RECEIPT_CLASS",
            "stray top-level 'receipt_class' is not an envelope field",
        )

    # GARP body-kind detail must live only under extensions.garp.body, never at
    # the top level.
    for key in GARP_BODY_DETAIL_KEYS:
        if key in receipt:
            result.add(
                "GARP_DETAIL_AT_TOP_LEVEL",
                f"GARP body detail '{key}' must live under "
                f"extensions.garp.body, not at the top level",
            )

    # No top-level body verdict / discriminator used as body semantics.
    for key in BODY_VERDICT_KEYS:
        if key in receipt:
            result.add(
                "TOP_LEVEL_BODY_VERDICT",
                f"top-level '{key}' is a body verdict/discriminator; the "
                f"envelope does not carry body verdicts",
            )

    # If GARP content is present, it must be nested as extensions.garp.body.
    extensions = receipt.get("extensions")
    if isinstance(extensions, dict) and "garp" in extensions:
        garp = extensions["garp"]
        if not isinstance(garp, dict) or "body" not in garp:
            result.add(
                "GARP_NOT_UNDER_BODY",
                "extensions.garp must nest GARP body-kind detail under "
                "extensions.garp.body",
            )


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------
def validate_receipt(
    receipt_path: Path, schema: dict
) -> Result:
    result = Result(str(receipt_path))
    try:
        receipt = load_json(receipt_path)
    except (OSError, json.JSONDecodeError) as exc:
        result.add("LOAD_ERROR", f"could not load receipt: {exc}")
        return result
    validate_against_schema(receipt, schema, result)
    enforce_envelope_guardrails(receipt, schema, result)
    return result


def _load_renderer():
    """Import the sibling plain-language renderer, or return None if absent.

    The renderer (tools/render_srs_envelope.py) is the intended human-output
    half of the verify command: validation says *whether* a receipt is a
    well-formed SRS envelope; the renderer says *what it says*, in plain words.
    The import is lazy and tolerant so the validator still runs as a pure
    pass/fail checker if the renderer is not present. Loaded by file location
    so it works whether or not `tools/` is on sys.path.
    """
    import importlib.util

    renderer_path = Path(__file__).resolve().parent / "render_srs_envelope.py"
    if not renderer_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(
        "render_srs_envelope", renderer_path
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_canonical(
    manifest_path: Path, schema_path: Path
) -> tuple[dict, dict, str]:
    """Load manifest + schema and verify the schema hash against the manifest.

    Returns (manifest, schema, schema_sha256). Raises SchemaHashMismatch if the
    schema bytes do not match the manifest's pinned digest.
    """
    manifest = load_json(manifest_path)
    schema = load_json(schema_path)
    digest = verify_schema_hash(schema_path, manifest)
    return manifest, schema, digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate receipts against the canonical ARCS SRS "
        "envelope schema (envelope conformance only).",
    )
    parser.add_argument(
        "receipts",
        nargs="*",
        type=Path,
        help="receipt JSON files to validate",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="path to the canonical schema manifest",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="path to the canonical schema",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="for each receipt that passes, also print the plain-language "
        "envelope reading produced by the standalone renderer "
        "(tools/render_srs_envelope.py). The reading is a reading aid; the "
        "JSON remains the authoritative artifact.",
    )
    args = parser.parse_args(argv)

    try:
        _manifest, schema, digest = load_canonical(args.manifest, args.schema)
    except SchemaHashMismatch as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FATAL: could not load canonical artifacts: {exc}", file=sys.stderr)
        return 2

    print(f"schema sha256 verified == manifest sha256: {digest}")

    if not args.receipts:
        print("no receipts given; schema identity verified only.")
        return 0

    renderer = _load_renderer() if args.render else None
    if args.render and renderer is None:
        print(
            "note: --render requested but tools/render_srs_envelope.py was not "
            "found; emitting pass/fail only.",
            file=sys.stderr,
        )

    any_failed = False
    for receipt_path in args.receipts:
        result = validate_receipt(receipt_path, schema)
        if result.ok:
            # Pass/fail line, then (optionally) the plain-language reading. The
            # reading is generated from the receipt's own fields and is a
            # reading aid only; the JSON stays authoritative.
            print(f"PASS  {receipt_path}  Valid SRS envelope 0.1.0.")
            if renderer is not None:
                try:
                    reading = renderer.render_receipt_file(receipt_path)
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    print(f"        [RENDER_ERROR] {exc}", file=sys.stderr)
                else:
                    print()
                    sys.stdout.write(reading)
                    print()
        else:
            any_failed = True
            print(f"FAIL  {receipt_path}  Invalid SRS envelope.")
            for code, message in result.errors:
                print(f"        [{code}] {message}")
    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
