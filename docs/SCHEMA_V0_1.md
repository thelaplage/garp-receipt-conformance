ARCS SRS Envelope Schema (vendored v0.1.0)
==========================================

Status: faithful, digest-pinned vendoring of the canonical ARCS SRS envelope
schema.

This document describes `schemas/srs-envelope/v0.1.0/srs-envelope.schema.json`,
a **byte-identical copy** of the canonical ARCS SRS envelope schema from
`arcs-srs`, and its pinned digest. The pack does not define its own schema; it
mirrors canonical. Any change to the schema is made upstream in `arcs-srs` first
and then re-vendored — the pack never edits, normalizes, reformats, or improves
the canonical bytes.

1. Source of truth and pin
--------------------------

- Source of truth: `arcs-srs`,
  `schemas/srs-envelope/v0.1.0/srs-envelope.schema.json`.
- Vendored copy: `schemas/srs-envelope/v0.1.0/srs-envelope.schema.json`.
- Manifest: `schemas/srs-envelope/v0.1.0/srs-envelope.schema.manifest.json`
  (also vendored byte-identical).
- Pinned SHA-256:

      e866eabf1cef537df6dc98f56f74021d8af585c94dc689f9fdd4ee97618d6b61

  recorded in `schemas/srs-envelope/v0.1.0/srs-envelope.schema.sha256` and in
  the manifest's `sha256` / `identity` fields.

Pinning is to `published_version` + `sha256`, **not** to a repository path. The
validator computes the schema file's digest and refuses to run unless it equals
the manifest's recorded digest, so the pin holds even if the canonical home
relocates.

Three distinct version markers, none invented:

- pack release marker — `v0.1`
- vendored schema version — `v0.1.0`
- receipt version carried by canonical receipts — `srs.core.v5.1`

2. What this schema validates
-----------------------------

The schema validates ARCS SRS **envelope form only**. It requires the following
top-level envelope fields:

- `receipt_version` — canonical SRS receipt version (e.g. `srs.core.v5.1`; the
  schema also accepts the legacy numeric form).
- `receipt_id`
- `receipt_type` — a **closed enum**: `sdk_enforcement`, `grace_session`,
  `connection`, `provenance`.
- `boundary_type`
- `protocol_binding`
- `subject_ref`
- `issued_at`
- `artifact_classes_covered`
- `artifact_classes_excluded`
- `attestation_limits`
- `extensions`

Optional fields include `retention_class_applied` and `receipt_signature` (a
string or a structured object). The canonical schema sets
`additionalProperties: true`; this quirk is preserved exactly as vendored.

Crucially, the envelope carries **no** top-level `schema_version` and **no**
top-level `body`. GARP body content lives only under `extensions.garp.body`
(see `BODY_KIND_EXTENSION_RULES.md`).

3. What this schema does NOT validate
-------------------------------------

The schema validates envelope form, not substance. In particular it does not
validate or prove:

- GARP body-kind conformance or any GARP body semantics,
- truth, correctness, admission, custody, or completeness of the receipt,
- public-surface eligibility of anything a receipt carries,
- absence of private-corpus leakage,
- real-world or external adoption,
- that any product/runtime behaved as claimed outside the receipt and fixture
  boundary.

See `ATTESTATION_LIMITS.md` for the full attestation-limit posture.

4. Verifying the pin from a clean checkout
------------------------------------------

    shasum -a 256 schemas/srs-envelope/v0.1.0/srs-envelope.schema.json
    shasum -c schemas/srs-envelope/v0.1.0/srs-envelope.schema.sha256

Any change to the schema bytes changes the digest. A new schema version is
published upstream as a new artifact with a new pinned digest and then
re-vendored, rather than by mutating this one.

5. How the validator and fixtures use it
----------------------------------------

`tools/validate_srs_envelope.py` (vendored canonical validator):

- loads the manifest and schema,
- computes the schema's sha256 and fails hard unless it matches the manifest,
- validates a receipt against the envelope schema (a small built-in subset
  check: type / required / enum / items / oneOf / properties),
- enforces envelope-only guardrails (closed `receipt_type` enum, required
  fields present, GARP detail only under `extensions.garp.body`, no top-level
  `receipt_class`, no top-level body verdict/discriminator).

`scripts/check_pack_v0_1.sh` runs the validator against every vendored fixture
and compares output to `expected/`. See `FIXTURES_V0_1.md`.

6. Provenance
-------------

`schemas/srs-envelope/v0.1.0/PROVENANCE.json` records the source repo, source
path, source sha256, copied sha256, and `copy_is_byte_identical: true` for the
schema, manifest, and validator. See `FIXTURE_PROVENANCE.md` for fixtures.
