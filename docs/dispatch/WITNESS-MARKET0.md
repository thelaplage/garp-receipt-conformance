# WITNESS-MARKET0

PROGRAM: COUNTERPEDIA-MARKET-WAVE3
REPO: thelaplage/garp-receipt-conformance
BASE: main
STATUS: DRAFT
AUTHORITY_MOVEMENT: 0

## Goal
Make receipt verification and independent byte witnessing discoverable market capabilities while preserving existing witness/receipt semantics.

## Invariant
`witness_offer_exists != witness_selected != receipt_observed != receipt_valid != action_authorized != result_true`

## Required work
- WitnessServiceOffer for receipt_verify, receipt_witness, receipt_store, replay_verify.
- Service guarantees describe observation/verification profiles only.
- WitnessRequest binds exact receipt digest and requested service.
- WitnessResult references native witness/verification artifacts; no truth or authority effect.
