ARCS SRS Envelope Conformance Fixtures (vendored)
=================================================

Status: faithful, byte-identical vendoring of the canonical ARCS SRS
conformance fixtures.

This document describes the conformance fixtures under `fixtures/valid/` and
`fixtures/invalid/`. Every fixture is a **byte-identical copy** of its source
under `arcs-srs/conformance/fixtures/`. The pack authors no fixtures and edits
none; provenance for each is recorded in `fixtures/PROVENANCE.json` (see
`FIXTURE_PROVENANCE.md`).

The fixtures exercise the ARCS SRS **envelope** schema only. They carry no real
customer, user, or matter data beyond what the canonical fixtures already
contain, and they validate from a clean public checkout with no private-corpus
access (see `NO_PRIVATE_CORPUS.md`).

1. Valid fixtures (exit 0)
--------------------------

One minimal valid receipt per closed `receipt_type` enum value, plus one real
envelope that transports a GARP body:

- `fixtures/valid/sdk_enforcement.minimal.json`
- `fixtures/valid/grace_session.minimal.json`
- `fixtures/valid/connection.minimal.json`
- `fixtures/valid/provenance.minimal.json`
- `fixtures/valid/compression_disposition.envelope.json` — a real, committed
  ARCS envelope carrying a full GARP body **under `extensions.garp.body`**. It
  is present as an **envelope-conformance fixture only**; it is not a GARP
  body-kind conformance target and its inclusion blesses nothing about that
  body.

2. Invalid fixtures (exit 1)
----------------------------

Each fails for exactly one stated envelope-level reason:

- `fixtures/invalid/receipt_type_outside_enum.json` — `receipt_type` outside the
  closed enum.
- `fixtures/invalid/missing_attestation_limits.json` — required
  `attestation_limits` absent.
- `fixtures/invalid/missing_artifact_classes_excluded.json` — required
  `artifact_classes_excluded` absent.
- `fixtures/invalid/garp_detail_at_top_level.json` — GARP body detail
  (`body_kind`, `retained_claims`) hoisted to the top level instead of living
  under `extensions.garp.body`. **This is the drift-form fixture**: it proves
  the reconciled pack actively refuses the shape that caused the schema drift.
- `fixtures/invalid/stray_top_level_receipt_class.json` — stray top-level
  `receipt_class`.
- `fixtures/invalid/top_level_verdict_discriminator.json` — top-level `verdict`
  used as a body-verdict discriminator.

3. Expected outputs
-------------------

For every fixture, `expected/valid/<name>.txt` or `expected/invalid/<name>.txt`
records the exact validator output. Each output begins with the verified schema
digest line, then a `PASS`/`FAIL` line, and — for failures — one machine-checkable
error code and message per stated reason. The expected outputs were regenerated
by running the vendored canonical validator against each fixture.

4. How the wrapper uses them
----------------------------

`scripts/check_pack_v0_1.sh`, from a clean checkout:

- confirms no whitespace/conflict damage and that every JSON artifact parses,
- verifies the pinned schema digest with `shasum -c`,
- runs `tools/validate_srs_envelope.py` against each **valid** fixture, expecting
  exit 0 and output matching `expected/valid/`,
- runs it against each **invalid** fixture, expecting exit 1 and output matching
  `expected/invalid/`.

5. Non-claims
-------------

These fixtures do not, by themselves:

- prove GARP body-kind conformance or bless any GARP body semantics,
- assert truth, admission, custody, or public-surface eligibility of any body,
- claim any external adoption,
- depend on any private corpus, private repository, or internal runtime state.
