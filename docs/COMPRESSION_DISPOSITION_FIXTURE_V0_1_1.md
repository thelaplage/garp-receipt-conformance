Compression-Disposition Fixture v0.1.1
======================================

Status: additive v0.1.1-compatible pack content (docs + fixtures only).

> **Retired bootstrap track.** This document describes the fixture in the retired
> bootstrap envelope shape — a divergent shape with a top-level `schema_version`,
> a top-level `body`, and a top-level `body_kind`, validated against
> `schemas/receipt-envelope-v0.1.schema.json`. That track is retired and those
> artifacts have been removed. The canonical SRS envelope now lives at
> `schemas/srs-envelope/v0.1.0/srs-envelope.schema.json`; the reconciled pack
> carries the canonical compression-disposition fixture at
> `fixtures/valid/compression_disposition.envelope.json`. See
> `docs/SCHEMA_V0_1.md` and `docs/BODY_KIND_EXTENSION_RULES.md`. The content
> below is retained for historical reference only.

This document describes the `compression_disposition` `body_kind` candidate
fixture added to the receipt envelope conformance pack:

- `fixtures/valid/receipt-envelope-compression-disposition-v0.1.1.json`
- `expected/valid-receipt-envelope-compression-disposition-v0.1.1.txt`

It is additive and non-breaking. The envelope schema
(`schemas/receipt-envelope-v0.1.schema.json`) and its pinned digest are
**unchanged**, no `body_kind`-specific schema or validation is added, and the
`body` remains opaque to the v0.1 envelope. The existing v0.1 fixtures and
checks continue to pass exactly as released.


1. What this fixture is
-----------------------

`receipt-envelope-compression-disposition-v0.1.1.json` is a single, valid,
public-safe receipt envelope whose `body_kind` candidate is the GARP
compression-disposition disposition body. It exercises the **envelope FORM**
only — the same surface the minimal fixture exercises — while carrying a body
payload whose internal field shape mirrors the pinned source renderer for
fidelity.

```json
{
  "schema_version": "0.1",
  "receipt_kind": "garp.compression.disposition",
  "body_kind": "garp.compression.disposition",
  "body": {
    "body_kind": "compression_disposition",
    "candidate_total": 4,
    "retained_claims": [
      { "candidate_ref": "claim_alpha", "source_ref": "src_one" },
      { "candidate_ref": "claim_beta", "source_ref": "src_two" }
    ],
    "refused_candidates": [
      {
        "candidate_ref": "claim_gamma",
        "lifecycle": "rejected",
        "reason": "candidate refused: support_state unsupported; no cited source attaches to the sentence."
      }
    ],
    "omitted_candidates": [],
    "artifact_hashes": {
      "packet.json": "sha256:aaaa",
      "trace.md": "sha256:bbbb"
    }
  }
}
```

All body values are synthetic tokens (`claim_alpha`, `src_one`, `packet.json`,
`sha256:aaaa`, …). They mirror the pinned source's full-body test fixture and
carry no matter, party, OCR, or corpus content. See `FIXTURE_PROVENANCE.md` and
`NO_PRIVATE_CORPUS.md`.


2. Why it is valid
------------------

It satisfies the four required envelope fields and adds no extra top-level keys,
so the strict `additionalProperties: false` envelope is satisfied:

- `schema_version` — `"0.1"`.
- `receipt_kind` — `"garp.compression.disposition"`, a conservative dotted
  token. The envelope schema does not constrain the set of kinds.
- `body_kind` — `"garp.compression.disposition"`, a conservative dotted token
  declaring (but not defining) a body vocabulary. The envelope registers no
  `body_kind`; it only requires that one be declared.
- `body` — an object. The envelope treats the body as opaque and asserts only
  that a body object is present, not its internal shape.

The local validator (`validator/validate_receipt_envelope_v0_1.py`) confirms
this; its expected output is recorded in
`expected/valid-receipt-envelope-compression-disposition-v0.1.1.txt` and is
diffed by `scripts/check_pack_v0_1.sh`.


3. Divergence A — envelope wrapper placement
--------------------------------------------

The conformance pack envelope and the pinned GARP renderer place `body_kind`
differently:

- **Conformance pack envelope** (this fixture, what the pack validates): carries
  `body_kind` at the **top level** and treats `body` as an opaque object.
- **Pinned GARP renderer** (the source, §6): reads the body at
  `extensions.garp.body` and dispatches on a `body_kind` carried **inside that
  body**.

One JSON document cannot be both a valid pack fixture and directly consumable by
the source renderer without transformation. This fixture resolves that honestly
and conservatively:

- it declares `body_kind` at the top level so it validates against the pack
  envelope, **and**
- its `body` carries the disposition payload — including an inner `body_kind`
  field — so the same body object could be rehosted under `extensions.garp.body`
  and read by the source renderer unchanged.

Under the v0.1 envelope schema the `body` is opaque (`type: object`), so the
inner `body_kind` is permitted and is **not** validated. It is intentional,
source-faithful redundancy, not a second source of truth.


4. Divergence B — identifier-token convention
---------------------------------------------

The pinned source's body-kind constant is the underscore token
`compression_disposition`. The conformance pack's validator
(`validate_receipt_envelope_v0_1.py`) enforces a **conservative dotted-token
pattern** at the envelope level — `^[a-z0-9]+(?:\.[a-z0-9]+)*$`, lowercase
alphanumeric tokens separated by single dots, **no underscores**. (The envelope
*schema* only requires a non-empty string; the validator is intentionally
stricter than the schema here.)

So an underscore token cannot appear at the validated envelope level. This
fixture resolves that as follows:

- **Envelope-level identifiers** use the conservative dotted token the validator
  permits: `receipt_kind` and `body_kind` are both
  `"garp.compression.disposition"`.
- **The opaque body** preserves the pinned source renderer token verbatim:
  `body.body_kind` is `"compression_disposition"`.

v0.1.1 keeps the body opaque and does **not** normalize, rewrite, or reinterpret
the inner body token. The dotted envelope identifier and the underscore body
constant coexist deliberately; reconciling them into one registered token is a
later, separately-approved decision (a v0.2 body-schema concern), not taken or
implied here.

This token divergence was not changed by relaxing the validator: no schema file
and no validator regex were modified for this fixture.


5. No body-content invalid fixture under v0.1
---------------------------------------------

No `compression_disposition`-specific *invalid* fixture is introduced, and none
can be honestly derived under v0.1.

A body-content invalid — e.g. `candidate_total` as a non-integer, a
`retained_claims` row missing `candidate_ref`, or a boolean-as-count — would
only be *rejectable* if a `body_kind`-specific body schema existed to reject it.
Under v0.1 the `body` is opaque (`type: object`), so every such document still
**passes** the envelope schema and validator. The pinned source renderer
*tolerates* all of them gracefully (rendering "not provided (not inferred)" or
weak lines) rather than treating them as invalid, so it provides **no** authority
for a body-content invalid fixture.

The only honest invalid for this candidate is at the **envelope** level and is
already covered by the existing `receipt-envelope-missing-body-v0.1.json`
pattern (required `body` removed); duplicating it under a
compression-disposition name would add no new envelope-level coverage, so it is
not added. A body-content invalid must wait for an explicitly approved v0.2 body
schema.


6. Provenance
-------------

The body field shape and synthetic values mirror the pinned GARP-side source
renderer and its full-body test fixture, as drafted and source-traced in the
garp-ops control-plane note
`IN___GARP_Compression_Disposition_Fixture_Shape_Draft_JUN01` (which composes
with the #80 source/provenance pin). The source is a read-only, deterministic,
stdlib-only renderer — not a schema, validator, or receipt emitter. This fixture
is a hand-authored synthetic artifact derived from that shape; it is not a
receipt emitted by any product or runtime, and no private source is included in
this pack.


7. Version
----------

This is **v0.1.1-compatible** pack content: additive fixtures + docs while the
envelope schema and its semantics are unchanged. It registers no `body_kind`
schema, adds no validation rule, and changes no existing behavior. Escalation to
v0.2 would be required only if `body_kind`-specific schema semantics (a
registered body schema with required/forbidden fields and a body-content invalid
fixture) were adopted — which is **not** done here.


8. Non-claims
-------------

This fixture and document do not, by themselves:

- represent any receipt emitted by a product or runtime — the fixture is
  synthetic test data authored by hand;
- add or register any `body_kind`-specific schema — the body stays opaque and no
  body vocabulary is defined or validated;
- normalize, validate, or assert meaning for the inner body token or any body
  field;
- claim any external adoption;
- prove any truth, correctness, compliance, security, or performance of
  anything — conformance remains a statement about envelope shape, not the
  world, and "refused" in the body is never restated as "false";
- depend on any private corpus, private repository, or internal runtime state.
