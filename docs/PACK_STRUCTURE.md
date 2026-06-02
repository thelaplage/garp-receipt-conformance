GARP Receipt Conformance Pack Structure
=======================================

Status: faithful, digest-pinned vendoring of the canonical ARCS SRS envelope
pack. The layout mirrors the `arcs-srs` `conformance/` layout for maximum
fidelity.

Layout
------

```
schemas/srs-envelope/v0.1.0/
  srs-envelope.schema.json            vendored canonical schema (pinned digest)
  srs-envelope.schema.manifest.json   vendored canonical manifest
  srs-envelope.schema.sha256          regenerated digest for shasum -c
  PROVENANCE.json                     byte-identical provenance: schema, manifest, validator

tools/
  validate_srs_envelope.py            vendored canonical validator (stdlib only)

fixtures/
  PROVENANCE.json                     byte-identical provenance for every fixture
  valid/                              one minimal receipt per receipt_type enum value,
                                       plus compression_disposition.envelope.json
  invalid/                           each fails for exactly one stated envelope reason

expected/
  valid/<name>.txt                    expected validator output per valid fixture
  invalid/<name>.txt                  expected validator output per invalid fixture

scripts/
  check_pack_v0_1.sh                  clean-checkout wrapper

docs/
  SCHEMA_V0_1.md                      vendored schema + pin
  BODY_KIND_EXTENSION_RULES.md        GARP body lives under extensions.garp.body
  FIXTURES_V0_1.md                    the vendored fixtures
  FIXTURE_PROVENANCE.md               provenance rules for all vendored artifacts
  PACK_STRUCTURE.md                   this file
  ATTESTATION_LIMITS.md               attestation-limit posture
  NO_PRIVATE_CORPUS.md                no-private-corpus rule
  CLEAN_CHECKOUT_V0_1.md              what the wrapper does and does not establish
  VALIDATOR_V0_1.md                   validator notes
  COMPRESSION_DISPOSITION_FIXTURE_V0_1_1.md  notes on the compression-disposition fixture

README.md                            verifier entry point
```

Version markers
---------------

Three distinct markers, none invented:

- pack release marker — `v0.1`
- vendored schema version — `v0.1.0`
- receipt version carried by canonical receipts — `srs.core.v5.1`

Vendoring posture
-----------------

`arcs-srs` is the source of truth. The schema, manifest, validator, and fixtures
are byte-identical copies of their `arcs-srs` sources, pinned by SHA-256. The
pack does not reference or submodule `arcs-srs` at runtime, so an outside
verifier can run it without trusting any private Vega Commons repository. Any
change to a canonical artifact is made upstream in `arcs-srs` first and then
re-vendored.

Non-claim
---------

This pack proves ARCS SRS **envelope** conformance only. It does not publish an
independent schema, does not bless GARP body-kind semantics, and does not assert
truth, admission, custody, or public-surface eligibility of anything a receipt
carries.
