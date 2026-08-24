Receipt-Witness Pack (v0.1)
============================

Status: first receipt-witness conformance pack in this repo. Implements
`docs/dispatch/RECEIPT-WITNESS0.md` (PROGRAM: COUNTERPEDIA-FEDERATED-PROOF0,
LANE: L03, STATUS: DRAFT, AUTHORITY_MOVEMENT: 0).

What this pack is
------------------

A `ReceiptWitnessObservation` is a signed claim of the form: *witness node W
observed exact receipt bytes with digest D by time T*. It says nothing else.
This pack proves the shape is real: independently verifiable, deterministic,
and structurally incapable of asserting more than that one claim.

```
schemas/receipt-witness-observation.v0.1.json   wire schema (repo root; shared, not vendored here)
tools/receipt_witness.py                        wire schema (repo root; dataclasses + validation)
scripts/check_receipt_witness.py                repo-level regression check (repo root)

packs/receipt-witness/v0.1/
  fixtures/valid/witness_a.json                 witness node A observing the fixture receipt digest
  fixtures/valid/witness_b.json                 witness node B observing the SAME digest, later
  fixtures/valid/witness_c.json                 witness node C observing the SAME digest, later still
  fixtures/invalid/*.json                        each fails for exactly one stated reason
  expected/valid/   expected/invalid/            byte-for-byte expected verifier output
  tools/verify_witness.py                        standalone verifier (stdlib only)
  check.sh                                        the pack conformance check
  README.md                                       this file
```

Run it from the repository root:

```
bash packs/receipt-witness/v0.1/check.sh
```

The check parses every fixture, verifies the three independent witness
fixtures each pass as valid byte-observations, confirms each invalid fixture
is rejected for exactly its one stated reason, proves the derived witness-set
aggregation is deterministic and order-independent, and re-runs the
repo-level regression script.

Required invariant
-------------------

    witnessed_bytes != valid_receipt != authorized_action != true_result
    != admitted_evidence

A witness observation says **"I observed these bytes by time T."** It does
not say "the receipt is a valid SRS envelope," "the action was authorized,"
"the result is true," or "this evidence is admitted." Those are four
different, independently-established claims that this pack never conflates:

- **witnessed_bytes** — this pack's only claim. Proven by
  `tools/verify_witness.py`: the observation is a well-formed, internally
  consistent `ReceiptWitnessObservation`.
- **valid_receipt** — a *different* claim, proven (for SRS envelopes) by
  `tools/validate_srs_envelope.py` at the repo root, against a *different*
  schema. A witness can observe bytes that later fail envelope validation;
  that is a fact this pack must be able to represent, not hide.
- **authorized_action** — a claim this pack never makes. No
  `authority_effect` (or any other authority/admission/trust-shaped) field
  is defined anywhere in the schema
  (`schemas/receipt-witness-observation.v0.1.json`) or the validator
  (`tools/receipt_witness.py`). "No authority" is expressed by that field's
  structural absence, not by a field pinned to a benign value: the schema's
  `additionalProperties: false` and the validator's closed field set mean an
  observation that tries to carry such a field is rejected outright,
  regardless of the value it carries (see
  `fixtures/invalid/authority_effect_violation.json`).
- **true_result / admitted_evidence** — claims this pack does not and cannot
  make. No field in the schema carries a verdict, a truth value, or an
  admission decision. The forbidden-field probe
  (`fixtures/invalid/additional_property_verdict.json`) demonstrates that a
  `verdict` field cannot even be smuggled onto the envelope — the schema's
  `additionalProperties: false` rejects it outright.

Verification API: byte-observation validity only
--------------------------------------------------

`tools.receipt_witness.verify_observation(data) -> ObservationVerification`
(used by `tools/verify_witness.py`) returns exactly one substantive field,
`byte_observation_valid`. The result also carries four fixed `asserts_*`
fields (`asserts_receipt_validity`, `asserts_action_authorization`,
`asserts_factual_truth`, `asserts_admission`), all hard-pinned `False` at the
dataclass level — not just documented, but structurally present on every
result — so a caller cannot read a passing verification as a stronger claim
without the result itself contradicting that reading.

Three-witness deterministic fixture
-------------------------------------

`fixtures/valid/witness_a.json`, `witness_b.json`, and `witness_c.json` are
three **independent** witness nodes (`node:witness-a/b/c`), each with its own
key id and signature value, each observing the **same** receipt digest at
three **distinct** `observed_at` timestamps. Run:

```
python3 packs/receipt-witness/v0.1/tools/verify_witness.py --witness-set \
    packs/receipt-witness/v0.1/fixtures/valid/witness_a.json \
    packs/receipt-witness/v0.1/fixtures/valid/witness_b.json \
    packs/receipt-witness/v0.1/fixtures/valid/witness_c.json
```

to produce the derived witness-set view (`tools.receipt_witness.build_witness_set`):
`receipt_digest`, `witness_count=3`, the sorted `witness_nodes`, and the sorted
`observation_digests`. This aggregation is **derived only** — the primary
observations remain independently addressable at their own paths/digests, the
aggregation never mutates them, and it is **order-independent**: `check.sh`
builds the set in forward and reverse fixture order and requires
byte-identical output.

Non-goals (explicit stop conditions)
--------------------------------------

- **No blockchain.** No chain, no block, no proof-of-work/-stake, no ledger
  consensus of any kind.
- **No consensus protocol.** Witnesses do not vote, do not need quorum, and
  do not reconcile disagreements with each other. Each observation is valid
  or invalid entirely on its own bytes.
- **No global timestamp authority.** `observed_at` is the witness node's own
  stated claim (schema-enforced UTC RFC3339 shape only); this pack does not
  introduce, call, or trust any external time-stamping authority (e.g. RFC
  3161 TSA) to corroborate it.
- **No truth-from-count.** `witness_count` is a count of independently
  addressable observations. It is never read, computed, or documented as
  stronger evidence of truth, validity, authorization, or admission. Three
  witnesses observing the same digest is three facts about observation, not
  one fact about truth.
- **No mutation of the witnessed receipt.** This pack never reads, edits, or
  regenerates the bytes a witness observation refers to; it only validates
  the observation record itself. (The fixture receipt digest here is a
  synthetic placeholder digest — no actual receipt file is required for this
  pack's checks, since only the *observation records* are conformance-tested.)
- **No equivalence with Counterpedia admission authority.** Nothing in this
  pack's schema, validator, or fixtures grants, implies, or stands in for
  admission. No authority- or admission-shaped field exists on the object at
  all; that structural absence, actively enforced by rejecting any attempt to
  add one, is this boundary.

Adapter seam (not implemented here)
--------------------------------------

The dispatch doc (`docs/dispatch/RECEIPT-WITNESS0.md`) notes a future adapter
seam for Countergraph lineage and later SAM transport metadata. This pack
introduces no such adapter and no optional transport-metadata field; the
schema stays closed (`additionalProperties: false`) until that seam is
scoped and built as its own lane.
