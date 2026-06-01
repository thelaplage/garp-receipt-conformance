Receipt Envelope Validator v0.1
===============================

Status: first public local validation command (Stage C4).

This document describes `validator/validate_receipt_envelope_v0_1.py`, the
first public local validation command for the GARP/SRS receipt conformance
pack, and the expected pass/fail outputs committed alongside it.

1. How to run the validator
---------------------------

From the repository root:

```
python3 validator/validate_receipt_envelope_v0_1.py <path-to-json>
```

For the committed fixtures:

```
python3 validator/validate_receipt_envelope_v0_1.py fixtures/valid/receipt-envelope-minimal-v0.1.json
python3 validator/validate_receipt_envelope_v0_1.py fixtures/invalid/receipt-envelope-missing-body-v0.1.json
```

Exit codes:

- `0` — envelope form is valid.
- `1` — envelope form is invalid (one or more rule violations).
- `2` — usage / IO / JSON-parse error (the document could not be evaluated).

The output is deterministic for a given input, so it can be diffed against the
committed expected-output files (see section 4). Diagnostic/usage messages for
exit code `2` go to stderr; the pass/fail report goes to stdout.

2. What it validates
--------------------

The validator checks **receipt envelope form only**, mirroring the required and
optional fields of `schemas/receipt-envelope-v0.1.schema.json`:

- top level must be a JSON object;
- `schema_version` — required, string, must equal `"0.1"`;
- `receipt_kind` — required, string matching a conservative dotted-token
  pattern (one or more lowercase alphanumeric tokens separated by single dots,
  e.g. `example.minimal`);
- `body_kind` — required, string matching the same dotted-token pattern;
- `body` — required, JSON object (treated as opaque — contents not inspected);
- `receipt_id` — optional; if present, a non-empty string;
- `issued_at` — optional; if present, an RFC 3339 / ISO 8601-ish date-time
  string (form only);
- `ext` — optional; if present, a JSON object;
- no additional top-level properties outside the set above (the envelope is
  strict).

3. What it does NOT validate
----------------------------

- It does not inspect or validate the `body` contents in any way. The body is
  opaque at the envelope layer.
- It does not perform any `body_kind`-specific schema validation. The set of
  valid `body_kind` values and their body shapes is out of scope here (see
  `docs/BODY_KIND_EXTENSION_RULES.md`).
- It does not assert that `issued_at` is real, accurate, or trusted — only that
  it has date-time form.
- It does not assert uniqueness, provenance, authenticity, or trust for
  `receipt_id` or any other field.
- It does not assert truth, correctness, compliance, security, or performance
  of anything described by the receipt.

4. Expected fixture outcomes
----------------------------

The committed expected outputs live in `expected/` and match the validator's
stdout byte-for-byte for the committed fixtures.

Valid fixture — `fixtures/valid/receipt-envelope-minimal-v0.1.json`
(expected: `expected/valid-receipt-envelope-minimal-v0.1.txt`), exit `0`:

```
PASS: receipt-envelope-minimal-v0.1.json
envelope-form valid against receipt-envelope v0.1
```

Invalid fixture — `fixtures/invalid/receipt-envelope-missing-body-v0.1.json`
(expected: `expected/invalid-receipt-envelope-missing-body-v0.1.txt`),
exit `1`:

```
FAIL: receipt-envelope-missing-body-v0.1.json
envelope-form invalid against receipt-envelope v0.1
  - body: required field missing
```

To compare actual against expected:

```
python3 validator/validate_receipt_envelope_v0_1.py fixtures/valid/receipt-envelope-minimal-v0.1.json \
  | diff -u expected/valid-receipt-envelope-minimal-v0.1.txt -
python3 validator/validate_receipt_envelope_v0_1.py fixtures/invalid/receipt-envelope-missing-body-v0.1.json \
  | diff -u expected/invalid-receipt-envelope-missing-body-v0.1.txt -
```

The validator reports the input by basename, so these comparisons are stable
regardless of the working directory from which the command is invoked.

5. Why the validator is stdlib-only
-----------------------------------

The validator uses only the Python 3 standard library (`json`, `re`, `sys`).
This keeps the public conformance pack trivially fetchable and runnable by an
outside verifier with nothing more than a stock Python 3 interpreter — no
`pip install`, no lockfile, no network access, and no third-party supply-chain
surface to trust. It keeps the validation step auditable in a single small
file.

6. Envelope-form validator, not a generic JSON Schema engine
------------------------------------------------------------

This command is a **v0.1 envelope-form validator**. It hand-implements the
specific v0.1 envelope rules listed in section 2; it does **not** implement a
generic JSON Schema (Draft 2020-12) evaluation engine. The schema artifact
`schemas/receipt-envelope-v0.1.schema.json` remains the normative description of
the envelope form; this validator is a minimal, dependency-free checker aligned
to it, not a general-purpose validator for arbitrary schemas.

7. Non-claims
-------------

This validator and its outputs make none of the following claims:

- No product/runtime receipt is emitted. The validator only inspects a JSON
  document supplied to it; it does not produce receipts.
- No external adoption is claimed or implied.
- No `body_kind`-specific schema validation is performed.
- No proof of truth, correctness, compliance, security, or performance is
  provided.
- No dependency on any private repository or private corpus exists; the
  validator runs entirely against the public artifacts in this pack.
