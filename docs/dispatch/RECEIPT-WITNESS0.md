# RECEIPT-WITNESS0

PROGRAM: COUNTERPEDIA-FEDERATED-PROOF0
LANE: L03
REPO: thelaplage/garp-receipt-conformance
BASE: main
STATUS: DRAFT
AUTHORITY_MOVEMENT: 0

## Goal
Define independently verifiable witness observations for immutable SRS receipt bytes so multiple nodes can attest that exact bytes were observed by a given time without attesting to truth, authorization, or admission.

## Required invariant
`witnessed_bytes != valid_receipt != authorized_action != true_result != admitted_evidence`.

## Deliverables
1. Versioned `ReceiptWitnessObservation` schema/model with receipt digest, witness node reference, observed-at timestamp, observation/signature envelope, and optional transport observation metadata.
2. Deterministic canonicalization and verification rules.
3. Conformance vectors for single witness, multiple independent witnesses, duplicate witness, invalid signature, mismatched digest, future timestamp, and revoked/unresolvable witness identity.
4. Verification API that returns byte-observation validity only; it must not upgrade the underlying receipt or action.
5. Aggregation helper producing a derived witness-set view while preserving individual observations as primary artifacts.
6. Fixture demonstrating three independent witness nodes observing one receipt digest at distinct times.
7. Explicit doctrine: a witness says `I observed these bytes by time T`, not `the receipt is true` and not `the action was legitimate`.
8. Adapter seam for Countergraph lineage and later SAM transport metadata.

## Stop conditions
- Do not create a blockchain, consensus protocol, or global timestamp authority.
- Do not collapse witness count into truth.
- Do not mutate the receipt being witnessed.
- Do not make witness identity equivalent to Counterpedia admission authority.

## Acceptance
Given one receipt and three witness observations, a verifier can independently prove which witnesses observed the exact receipt digest and when, while every higher-order epistemic/authority claim remains explicitly unproven.
