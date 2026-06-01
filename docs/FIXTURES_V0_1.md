Receipt Envelope Fixtures v0.1
==============================

Status: first public fixtures (Stage C3).

This document describes the first public receipt envelope fixtures for schema
`schemas/receipt-envelope-v0.1.schema.json`. The fixtures exercise the
**envelope-level** schema only: one envelope that is valid by construction and
one that fails for a simple, envelope-level reason.

The fixtures are synthetic, minimal, and public-safe. They carry no real
customer, user, or matter data, derive from no private corpus, and reference no
private repository. The `body` is intentionally kept opaque and empty so that no
`body_kind`-specific meaning is implied.

1. Fixture list
---------------

- `fixtures/valid/receipt-envelope-minimal-v0.1.json` — a minimal envelope that
  satisfies the schema.
- `fixtures/invalid/receipt-envelope-missing-body-v0.1.json` — the same minimal
  envelope with the required `body` field removed.

Both fixtures target the version marker `0.1` (see `SCHEMA_V0_1.md`).

2. Why the valid fixture is valid
---------------------------------

`receipt-envelope-minimal-v0.1.json` contains exactly the four required envelope
fields and nothing else:

- `schema_version` — `"0.1"`, a non-empty string matching the schema's
  `^[0-9]+\.[0-9]+(?:\.[0-9]+)?$` pattern.
- `receipt_kind` — `"example.minimal"`, a non-empty string. The envelope schema
  does not constrain the set of kinds.
- `body_kind` — `"example.opaque"`, a non-empty string declaring (but not
  defining) a body vocabulary. The envelope schema registers no `body_kind`; it
  only requires that one be declared.
- `body` — `{}`, an object. The envelope treats the body as opaque and asserts
  only that a body object is present, not its internal shape.

No optional fields (`receipt_id`, `issued_at`, `ext`) are used, and no extra
top-level keys are present, so the strict `additionalProperties: false` envelope
constraint is satisfied. The fixture is therefore valid by construction.

3. Why the invalid fixture is invalid
-------------------------------------

`receipt-envelope-missing-body-v0.1.json` is identical to the valid fixture
except that the required `body` field is omitted. The schema lists `body` in its
`required` array, so a verifier must reject this envelope for a missing required
property.

This is deliberately a single, simple, envelope-level failure. It does not rely
on body contents, optional fields, format assertions, or any
`body_kind`-specific rule — it fails purely because a required envelope field is
absent.

4. How these fixtures will be used by the future validator
----------------------------------------------------------

These fixtures are inert data. A future validator (out of scope for this PR)
will, per `SCHEMA_V0_1.md`:

- load `schemas/receipt-envelope-v0.1.schema.json`,
- confirm the loaded bytes match the pinned digest in
  `schemas/receipt-envelope-v0.1.sha256`,
- validate `fixtures/valid/receipt-envelope-minimal-v0.1.json` and expect it to
  **pass**,
- validate `fixtures/invalid/receipt-envelope-missing-body-v0.1.json` and expect
  it to **fail** (missing required `body`),
- compare both results against expected pass/fail records in `expected/`.

The fixtures are validatable from a clean public checkout without private-corpus
access (see `NO_PRIVATE_CORPUS.md` and `FIXTURE_PROVENANCE.md`).

5. Scope of this PR
-------------------

This PR adds **only** the two fixtures above and this document. It does not add
validator code, expected-output records, or any product/runtime code. Those
arrive in later stages.

6. Non-claims
-------------

These fixtures do not, by themselves:

- represent any receipt emitted by a product or runtime — they are synthetic
  test data authored by hand,
- demonstrate validation by any committed validator — no validator is included
  in this PR, so neither fixture has been checked by a committed validator yet,
- add or register any `body_kind`-specific schema — the body stays opaque and no
  body vocabulary is defined,
- claim any external adoption,
- prove any product or runtime behavior,
- depend on any private corpus, private repository, or internal runtime state.
