# SAM-EXECUTION-RECEIPT0

## Mission

Define and verify a portable execution receipt for a remote MCP invocation carried over SAM, without treating transport authentication or successful execution as evidentiary truth, admission, or publication.

SAM is the first transport adapter. The receipt shape must remain usable for other transports.

## Required outputs

1. A versioned execution-receipt schema and canonicalization rules.
2. Conformance fixtures for a successful invocation, refusal/denial, transport failure, and contaminated/malformed response.
3. A verifier that recomputes deterministic receipt identity and rejects authority/standing injection.
4. A thin SAM projection fixture/adapter showing how current SAM observations populate the portable receipt.
5. Documentation of what a valid receipt proves and explicitly does not prove.

## Minimum receipt content

Where observed and available:
- receipt/version identifier
- invocation identifier
- caller/principal identity reference
- target service/node identity reference
- MCP tool identity/name
- canonical arguments digest
- request observation/time
- transport/session observation reference
- policy/decision reference when one exists
- execution outcome enum
- returned payload digest or explicit `unavailable`
- error/refusal observation when applicable
- parent/delegation/lineage references when supplied
- transport adapter identifier and source revision

Do not synthesize missing SAM observations. Use explicit `unavailable`/`not_observed` states according to the repo's conventions.

## Core non-equivalences

`receipt_valid != action_authorized`

`receipt_valid != output_true`

`receipt_valid != output_evidence_supported`

`receipt_valid != admitted`

`receipt_valid != published`

A receipt proves only that the receipt structure is internally valid and that its bound observations/digests verify under the stated conformance rules.

## Security/adversarial requirements

Reject attempts to inject or infer:
- `verified=true`
- `published=true`
- `admitted=true`
- evidence/support standing not present in licensed upstream contracts
- broader delegated authority than the decision/delegation reference licenses

Distinguish caller identity, transport identity, service identity, and content/artifact identity.

## Determinism

Canonical serialization must be stable. Equivalent inputs must produce identical receipt digests. Field ordering, optional/unavailable state, timestamps, and adapter metadata must have explicit rules.

## Integration seam

If the repo already has a canonical receipt family, extend or profile it rather than inventing a competing authority-bearing receipt. Preserve existing contracts and document any unresolved mismatch.

## Acceptance gates

- Positive SAM invocation fixture verifies.
- Reordering JSON fields does not change canonical receipt identity.
- Argument mutation changes the bound digest and invalidates a mismatched receipt.
- Returned-payload mutation changes the bound digest and invalidates a mismatched receipt.
- Refusal and transport failure produce valid non-success receipts rather than fake success receipts.
- Unknown/unsupported SAM fields do not silently acquire meaning.
- Authority/standing injection fixtures fail.
- Existing conformance suites remain green.
- `AUTHORITY_MOVEMENT = 0`.

## STOP conditions

STOP if a required field cannot be observed from current SAM/DAGR-MCP surfaces; mark it unresolved rather than fabricating it. STOP if implementation would redefine an existing constitutional receipt or grant execution authority.

## PR posture

DRAFT only. Do not merge. Report schema/version, digest domain, fixtures, verifier results, SAM source pins, unresolved fields, and `AUTHORITY_MOVEMENT`.