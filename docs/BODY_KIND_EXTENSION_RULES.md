body_kind Extension Rules
=========================

Status: enforced by the vendored canonical validator.

This pack proves ARCS SRS **envelope** conformance only. It does not bless any
GARP body-kind semantics. This document states where GARP body content is
allowed to live and how the envelope refuses the shapes that would smuggle body
semantics into the envelope.

1. GARP body content lives under `extensions.garp.body`
-------------------------------------------------------

GARP body-kind content — including `body_kind` and its detail — lives **only**
under `extensions.garp.body`. It is **never**:

- a top-level `body`, and
- never selected by a top-level `body_kind`.

The canonical envelope carries no top-level `schema_version` and no top-level
`body`. A receipt that hoists body content to the top level is **not** a valid
SRS envelope and is rejected.

A real, committed example is the vendored
`fixtures/valid/compression_disposition.envelope.json`: it carries a full GARP
body — `body_kind`, `retained_claims`, `refused_candidates`,
`omitted_candidates`, `candidate_total`, `artifact_hashes` — entirely nested
under `extensions.garp.body`. Its inclusion demonstrates that a valid ARCS
envelope can transport a GARP body; it blesses nothing about that body.

2. What the validator refuses
-----------------------------

`tools/validate_srs_envelope.py` enforces the following envelope-only
guardrails on top of schema validation:

- **GARP detail at the top level is rejected.** The keys `body_kind`,
  `retained_claims`, `refused_candidates`, `omitted_candidates`,
  `candidate_total`, and `artifact_hashes` are legitimate only under
  `extensions.garp.body`; at the top level they raise
  `GARP_DETAIL_AT_TOP_LEVEL`. See
  `fixtures/invalid/garp_detail_at_top_level.json`.
- **A stray top-level `receipt_class` is rejected** (`TOP_LEVEL_RECEIPT_CLASS`).
  See `fixtures/invalid/stray_top_level_receipt_class.json`.
- **A top-level body verdict / discriminator is rejected.** A top-level
  `verdict`, `admitted`, `refused`, `held`, or `status` used as a body verdict
  raises `TOP_LEVEL_BODY_VERDICT`; the envelope never carries a body verdict.
  See `fixtures/invalid/top_level_verdict_discriminator.json`.
- **If `extensions.garp` is present, it must nest detail under
  `extensions.garp.body`** (`GARP_NOT_UNDER_BODY`).
- **`receipt_type` must be in the closed enum** `sdk_enforcement`,
  `grace_session`, `connection`, `provenance` (`RECEIPT_TYPE_NOT_IN_ENUM`).

3. The retired bootstrap shape is refused
-----------------------------------------

Earlier drafts of this pack used a divergent bootstrap envelope with a top-level
`schema_version`, a top-level `body`, and a top-level `body_kind`. That track is
retired. A receipt in that shape fails validation against the canonical schema:
it is missing every required envelope field, and its top-level `body_kind` trips
the `GARP_DETAIL_AT_TOP_LEVEL` guardrail. The reconciled pack actively refuses
the shape that caused the drift.

4. Adding a body-kind upstream
------------------------------

Body-kind semantics are out of scope for this pack and are not defined here. Any
future body-kind work is authored and tested in the canonical SRS lane
(`arcs-srs`); this pack only ever vendors what that lane publishes, byte for
byte. It defines no body-kind of its own.
