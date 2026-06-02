GARP Receipt Conformance
========================

Status: faithful, digest-pinned vendoring of the canonical ARCS SRS envelope.

This repository is the standalone public conformance-pack target for GARP/SRS
receipt externalization. It is a **byte-identical mirror** of the canonical ARCS
SRS envelope schema **v0.1.0** — the schema carried by receipts that declare
`receipt_version: "srs.core.v5.1"` — together with the canonical validator,
schema manifest, and conformance fixtures.

Its purpose is to let an outside verifier fetch a minimal public pack, validate
emitted receipts against a pinned schema and digest, compare expected pass/fail
behavior, and understand the attestation limits **without trusting Vega Commons
private repositories**. To keep that guarantee, the pack is self-contained: it
**vendors** the canonical artifacts rather than referencing or submoduling the
source repository at runtime.

Source of truth and pin
-----------------------

- Source of truth: `arcs-srs`. The pack copies its artifacts byte-identical and
  never edits, normalizes, reformats, or "improves" them. Any change to a
  canonical artifact is made upstream in `arcs-srs` first and then re-vendored.
- Canonical schema: `schemas/srs-envelope/v0.1.0/srs-envelope.schema.json`,
  pinned by SHA-256:

      e866eabf1cef537df6dc98f56f74021d8af585c94dc689f9fdd4ee97618d6b61

  recorded in `schemas/srs-envelope/v0.1.0/srs-envelope.schema.sha256` and in
  the schema manifest. **Pinning is to `published_version` + `sha256`, not to a
  repository path.** The validator computes the schema's digest and refuses to
  run unless it equals the manifest's recorded digest.
- Three distinct version markers, none invented:
  - pack release marker — `v0.1`
  - vendored schema version — `v0.1.0`
  - receipt version carried by canonical receipts — `srs.core.v5.1`

What this pack proves
---------------------

ARCS SRS **envelope** conformance only. It does **not** prove GARP body-kind
conformance, does **not** bless any GARP body semantics, and does **not** assert
truth, admission, custody, or public-surface eligibility of anything a receipt
carries. GARP body content lives only under `extensions.garp.body`; it is never
a top-level `body` with a top-level `body_kind` (see
`docs/BODY_KIND_EXTENSION_RULES.md`).

Pack contents
-------------

- `schemas/srs-envelope/v0.1.0/srs-envelope.schema.json` — vendored canonical
  schema (pinned digest above).
- `schemas/srs-envelope/v0.1.0/srs-envelope.schema.manifest.json` — vendored
  canonical manifest.
- `schemas/srs-envelope/v0.1.0/srs-envelope.schema.sha256` — regenerated digest
  for `shasum -c`.
- `schemas/srs-envelope/v0.1.0/PROVENANCE.json` — byte-identical provenance for
  the schema, manifest, and validator.
- `tools/validate_srs_envelope.py` — vendored canonical validator (Python 3
  standard library only).
- `fixtures/valid/` and `fixtures/invalid/` — vendored canonical conformance
  fixtures.
- `fixtures/PROVENANCE.json` — byte-identical provenance for every fixture.
- `expected/valid/` and `expected/invalid/` — expected validator output per
  fixture.
- `scripts/check_pack_v0_1.sh` — clean-checkout wrapper.
- `docs/` — verifier documents: schema, body-kind extension rules, fixtures,
  fixture provenance, pack structure, attestation limits, the boundary_type
  posture, and the no-private-corpus rule.

Run it from a clean checkout
----------------------------

No install step, no third-party dependencies — Python 3 standard library and
stock POSIX tooling only. From the repository root:

    bash scripts/check_pack_v0_1.sh

The wrapper verifies there is no whitespace/conflict damage, parses every JSON
artifact, checks the pinned schema digest with `shasum -c`, validates each valid
fixture (exit 0, output matching `expected/valid/`), and confirms each invalid
fixture is rejected (exit 1, output matching `expected/invalid/`).

Packs built on this envelope
----------------------------

Beyond the vendored envelope pack above, `packs/` holds receipt-bearing packs
that build receipts from explicit, public-safe input and validate them against
the canonical schema vendored here. Each pack is self-contained, carries its own
`check.sh`, and proves **structural and cryptographic integrity only** — never
truth.

- `packs/mcp-audit-trail/v0.1/` — the first **vendor-neutral** pack: a public-safe
  MCP (Model Context Protocol) custody-gateway audit-trail input, a minimal
  deterministic adapter that builds an SRS envelope receipt from it, and the
  conformance fixtures. It preserves Option A / `decision_ref` and introduces no
  vendor profile. It is the neutral pack that proves the shape. Run:
  `bash packs/mcp-audit-trail/v0.1/check.sh`.
- `packs/bedrock-openai-audit/v0.1/` — the first **vendor-specific** pack. It
  **instantiates the neutral shape above** (same canonical schema, same envelope
  invariants, same Option A / `decision_ref` discipline, same `boundary_type`
  routing value) using an explicit, public-safe, **synthetic** Bedrock/OpenAI
  model-invocation custody/audit input. It is **not** a live integration: no AWS,
  OpenAI, or Bedrock API is called, no credentials or env vars are read, and it
  makes no claim about any model output (verifies none). Run:
  `bash packs/bedrock-openai-audit/v0.1/check.sh`.

Repository roles
----------------

`arcs-srs` is the canonical source of truth for the envelope schema, validator,
and fixtures. This repository is the canonical standalone **verifier target**: a
self-contained, digest-pinned copy an outside party can run without access to
any private Vega Commons repository.
