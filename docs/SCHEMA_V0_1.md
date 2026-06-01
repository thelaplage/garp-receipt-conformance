Receipt Envelope Schema v0.1
============================

Status: first public schema artifact (Stage C2).

This document describes `schemas/receipt-envelope-v0.1.schema.json`, the first
public schema artifact for the GARP/SRS receipt conformance pack, and its
pinned digest/version marker.

1. What this schema validates
-----------------------------

The schema validates **receipt envelope form only**. It is a minimal,
envelope-level JSON Schema (Draft 2020-12) that asserts an envelope carries the
structural fields a verifier needs to route and version a receipt.

Required envelope fields:

- `schema_version` — version marker the receipt declares conformance to.
- `receipt_kind` — stable identifier for the kind of receipt.
- `body_kind` — stable identifier selecting the body vocabulary/schema. This is
  the documented extension point (see `BODY_KIND_EXTENSION_RULES.md`).
- `body` — the receipt payload object.

Optional envelope fields:

- `receipt_id` — opaque per-instance identifier.
- `issued_at` — RFC 3339 / ISO 8601 date-time.
- `ext` — controlled extension namespace for not-yet-standardized
  envelope-level fields.

Posture on extra fields: the top-level envelope is **strict**
(`additionalProperties: false`). Controlled extension is funneled through the
explicit `ext` object so the envelope can stay strict while remaining
forward-compatible. The `body` object is intentionally **opaque** at this layer:
the envelope asserts only that a `body` object is present, not its internal
shape.

2. What this schema does NOT validate
-------------------------------------

The schema validates form, not substance. In particular it does not validate or
prove:

- the internal shape or contents of `body` (that is the future
  `body_kind`-specific schema's job),
- truth, correctness, or completeness of the receipt,
- legal compliance, security, or performance,
- admission or provenance of any source material,
- absence of private-corpus leakage,
- real-world or external adoption,
- that any product/runtime behaved as claimed outside the receipt and fixture
  boundary.

See `ATTESTATION_LIMITS.md` for the full attestation-limit posture.

3. Digest / version marker
--------------------------

The version marker is `v0.1`, reflected in the artifact filename, the schema
`$id`, the `title`/`description`, and the `schema_version` value the schema
expects (`"0.1"`).

The artifact is pinned by a SHA-256 digest recorded in
`schemas/receipt-envelope-v0.1.sha256`, in standard `sha256sum`-style format
(hex digest, two spaces, filename).

To verify the pin from a clean public checkout:

    shasum -a 256 schemas/receipt-envelope-v0.1.schema.json
    # or, from inside schemas/:
    cd schemas && shasum -a 256 -c receipt-envelope-v0.1.sha256

Any change to the schema bytes changes the digest. A new schema version will be
published as a new artifact and a new pinned digest rather than by mutating this
one.

4. How future fixtures will use it
----------------------------------

When fixtures are added in a later stage, each fixture's metadata will reference
this schema by version and digest (see `FIXTURE_PROVENANCE.md`). A future
validator will:

- load `schemas/receipt-envelope-v0.1.schema.json`,
- confirm the loaded bytes match the pinned digest,
- validate `fixtures/valid/*` as schema-conformant envelopes,
- confirm `fixtures/invalid/*` are rejected,
- compare results against expected pass/fail outputs in `expected/`.

Fixtures must be public-safe and validatable from a clean public checkout
without private-corpus access (see `NO_PRIVATE_CORPUS.md`).

5. Scope of this PR
-------------------

This PR adds **only** the schema artifact, its pinned digest file, and this
document. It does not add fixtures and does not add validator code. Those arrive
in later stages.

6. Non-claims
-------------

This artifact does not, by itself:

- emit any receipt,
- validate any fixture,
- register any `body_kind` beyond the envelope schema vocabulary (the envelope
  only requires that a `body_kind` be declared; it defines none),
- claim any external adoption,
- prove any product or runtime behavior,
- depend on any private corpus, private repository, or internal runtime state.
