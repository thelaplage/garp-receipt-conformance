GARP Receipt Conformance
========================

Status: bootstrap skeleton only.

This repository is the standalone public conformance-pack target for GARP/SRS receipt externalization.

Its purpose is to let an outside verifier fetch a minimal public pack, validate emitted receipts against a pinned schema/version, compare expected pass/fail behavior, and understand the attestation limits without trusting Vega Commons private repositories.

Current state
-------------

This bootstrap commit does not publish a receipt schema, does not register a body_kind, does not implement a validator, does not emit a receipt, does not validate a fixture, and does not claim external adoption.

Planned pack contents
---------------------

- Fetchable schema artifact
- Pinned schema digest/version marker
- Valid fixture receipt
- Invalid fixture receipt
- Local validation command
- Expected pass/fail output
- Verifier README
- body_kind extension rules
- Attestation limits
- Fixture provenance rules
- No-private-corpus rule

Repository roles
----------------

garp-ops remains the planning and gate record.

garp-sdk may produce receipt contracts and fixture candidates, but is not the sole external verifier surface.

garpedia_org may explain the method after gates pass, but is not the canonical conformance target.

This repository is the canonical standalone verifier target.
