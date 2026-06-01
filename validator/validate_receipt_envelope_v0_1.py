#!/usr/bin/env python3
"""Local validator for GARP/SRS receipt envelope schema v0.1.

This is a small, deterministic, envelope-FORM validator. It checks that a
candidate JSON document carries the structural envelope fields described by
``schemas/receipt-envelope-v0.1.schema.json``. It is intentionally NOT a
generic JSON Schema engine: it hand-implements only the v0.1 envelope rules.

Scope and non-claims (see docs/VALIDATOR_V0_1.md):
  - Validates envelope FORM only. The ``body`` is treated as opaque.
  - Does NOT perform body_kind-specific validation.
  - Does NOT emit a product/runtime receipt.
  - Does NOT assert truth, correctness, compliance, security, performance,
    provenance, or any external adoption.
  - Does NOT depend on any private repo or private corpus.

Usage:
  python3 validator/validate_receipt_envelope_v0_1.py <path-to-json>

Exit codes:
  0  envelope form is valid
  1  envelope form is invalid (one or more rule violations)
  2  usage / IO / JSON-parse error (could not evaluate the document)
"""

import json
import re
import sys

SCHEMA_VERSION_EXPECTED = "0.1"

# Conservative dotted-token pattern: one or more lowercase alphanumeric tokens
# separated by single dots (e.g. "example.minimal"). No leading/trailing dot,
# no empty tokens, no uppercase, no whitespace.
DOTTED_TOKEN_RE = re.compile(r"^[a-z0-9]+(?:\.[a-z0-9]+)*$")

# RFC 3339 / ISO 8601-ish date-time: YYYY-MM-DDThh:mm:ss[.frac](Z|+hh:mm|-hh:mm).
# Form check only; does not assert the timestamp is real, accurate, or trusted.
DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?"
    r"([Zz]|[+-]\d{2}:\d{2})$"
)

# Top-level properties recognized by the v0.1 envelope. Any other top-level
# key is an additional-property violation (the envelope is strict).
ALLOWED_KEYS = (
    "schema_version",
    "receipt_kind",
    "body_kind",
    "body",
    "receipt_id",
    "issued_at",
    "ext",
)


def validate_envelope(doc):
    """Return a deterministically ordered list of envelope-form error strings.

    An empty list means the document is a valid v0.1 envelope FORM.
    """
    errors = []

    if not isinstance(doc, dict):
        return ["root: must be a JSON object"]

    # schema_version: required, string, exactly "0.1".
    if "schema_version" not in doc:
        errors.append("schema_version: required field missing")
    else:
        value = doc["schema_version"]
        if not isinstance(value, str):
            errors.append("schema_version: must be a string")
        elif value != SCHEMA_VERSION_EXPECTED:
            errors.append(
                'schema_version: must equal "%s"' % SCHEMA_VERSION_EXPECTED
            )

    # receipt_kind / body_kind: required, non-empty dotted-token strings.
    for key in ("receipt_kind", "body_kind"):
        if key not in doc:
            errors.append("%s: required field missing" % key)
        else:
            value = doc[key]
            if not isinstance(value, str):
                errors.append("%s: must be a string" % key)
            elif not DOTTED_TOKEN_RE.match(value):
                errors.append(
                    "%s: must match conservative dotted-token pattern "
                    "(lowercase alphanumeric tokens separated by dots)" % key
                )

    # body: required object.
    if "body" not in doc:
        errors.append("body: required field missing")
    elif not isinstance(doc["body"], dict):
        errors.append("body: must be a JSON object")

    # receipt_id: optional, non-empty string if present.
    if "receipt_id" in doc:
        value = doc["receipt_id"]
        if not isinstance(value, str):
            errors.append("receipt_id: must be a string")
        elif len(value) < 1:
            errors.append("receipt_id: must be a non-empty string")

    # issued_at: optional, RFC 3339-ish date-time string if present.
    if "issued_at" in doc:
        value = doc["issued_at"]
        if not isinstance(value, str):
            errors.append("issued_at: must be a string")
        elif not DATE_TIME_RE.match(value):
            errors.append(
                "issued_at: must be an RFC 3339 / ISO 8601 date-time string"
            )

    # ext: optional object if present.
    if "ext" in doc:
        if not isinstance(doc["ext"], dict):
            errors.append("ext: must be a JSON object")

    # Strict top-level: no additional properties. Sorted for determinism.
    extra = sorted(k for k in doc if k not in ALLOWED_KEYS)
    for key in extra:
        errors.append("%s: additional top-level property not allowed" % key)

    return errors


def main(argv):
    if len(argv) != 2:
        sys.stderr.write(
            "usage: python3 validator/validate_receipt_envelope_v0_1.py "
            "<path-to-json>\n"
        )
        return 2

    path = argv[1]
    name = path.replace("\\", "/").rsplit("/", 1)[-1]

    try:
        with open(path, "r", encoding="utf-8") as handle:
            doc = json.load(handle)
    except OSError as exc:
        sys.stderr.write("ERROR: cannot read %s: %s\n" % (name, exc.strerror))
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write("ERROR: %s is not valid JSON: %s\n" % (name, exc.msg))
        return 2

    errors = validate_envelope(doc)

    if not errors:
        print("PASS: %s" % name)
        print("envelope-form valid against receipt-envelope v0.1")
        return 0

    print("FAIL: %s" % name)
    print("envelope-form invalid against receipt-envelope v0.1")
    for error in errors:
        print("  - %s" % error)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
