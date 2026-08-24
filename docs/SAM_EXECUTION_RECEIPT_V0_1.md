SAM Execution-Receipt Schema and Canonicalization (v0.1)
==========================================================

Status: **DRAFT**, dispatch lane `SAM-EXECUTION-RECEIPT0`, `AUTHORITY_MOVEMENT
= 0`. Implementation: `packs/sam-execution-receipt/v0.1/`.

This document describes the **portable execution receipt** for a remote MCP
tool invocation carried over SAM (the first transport adapter this shape is
proven for), the fields it carries, and the canonicalization rules its
identity digest depends on. It is a companion to
`packs/sam-execution-receipt/v0.1/README.md`, which describes what a receipt
built to this shape proves and does not prove.

1. What this is, and what it is not
------------------------------------

This is **not** a new top-level receipt family. It is a **profile**: a new
GARP `body_kind` (`sam_execution_receipt`) carried under
`extensions.garp.body` of the existing canonical ARCS SRS envelope
(`schemas/srs-envelope/v0.1.0/srs-envelope.schema.json`), using the existing
closed-enum `receipt_type` value `sdk_enforcement` -- the family this repo
already carries for SDK/transport-binding enforcement decisions over a tool
call. See "Integration seam" in `docs/dispatch/SAM-EXECUTION-RECEIPT0.md`:
*"If the repo already has a canonical receipt family, extend or profile it
rather than inventing a competing authority-bearing receipt."*

`boundary_type` is `sdk_enforcement_boundary` -- a pack-local descriptive
routing label, not a canonical value. See `docs/BOUNDARY_TYPE_LEDGER.md` and
`docs/BOUNDARY_TYPE_POSTURE.md`.

2. Version markers
-------------------

Four distinct version markers, none invented beyond the one this lane adds:

- pack release marker -- `v0.1` (`packs/sam-execution-receipt/v0.1/`)
- vendored envelope schema version -- `v0.1.0` (unchanged; not re-vendored)
- receipt version carried by canonical receipts -- `srs.core.v5.1` (unchanged)
- **body schema version, new in this lane** --
  `extensions.garp.body.execution_receipt_schema_version` =
  `"sam-execution-receipt/v0.1"`. This versions the body_kind's field set
  independently of the envelope schema, so a future revision of this body
  shape can be introduced without touching the envelope.

3. Envelope-level fields (unchanged from the canonical schema)
------------------------------------------------------------------

All envelope-level fields are exactly as required by
`schemas/srs-envelope/v0.1.0/srs-envelope.schema.json` (see
`docs/SCHEMA_V0_1.md`). This profile fixes the following envelope-level
values:

| field | value |
|---|---|
| `receipt_type` | `sdk_enforcement` (existing closed enum value) |
| `boundary_type` | `sdk_enforcement_boundary` (pack-local descriptive) |
| `protocol_binding` | `garp` |
| `subject_ref` | the invocation's `invocation_id` |
| `retention_class_applied` | `hash_only` |
| `artifact_classes_covered` | `["trace", "packet_inspection"]` |
| `artifact_classes_excluded` | `["truth_verification", "action_authorization", "publication_eligibility", "evidentiary_support_determination"]` |

4. Body fields (`extensions.garp.body`, `body_kind = "sam_execution_receipt"`)
------------------------------------------------------------------------------

"Where observed and available" per the dispatch lane's minimum-content list.
A field that was not observed is **omitted** (never fabricated), except
`returned_payload_digest`, which uses the explicit sentinel described in
section 5.

| field | required? | maps to lane requirement | notes |
|---|---|---|---|
| `body_kind` | always | receipt/version identifier | literal `"sam_execution_receipt"` |
| `execution_receipt_schema_version` | always | receipt/version identifier | literal `"sam-execution-receipt/v0.1"` |
| `invocation_id` | always | invocation identifier | opaque string, also the envelope `subject_ref` |
| `caller_ref` | always | caller/principal identity reference | opaque reference, never a raw credential |
| `target_ref` | always | target service/node identity reference | opaque reference |
| `mcp_tool_ref` | always | MCP tool identity/name | dotted tool name |
| `canonical_arguments_digest` | always | canonical arguments digest | `sha256:<hex>`; arguments themselves are never carried (metadata-only) |
| `requested_at` | always | request observation/time | RFC 3339 UTC, distinct from envelope `issued_at` (issuance time) |
| `transport_session_ref` | always | transport/session observation reference | opaque reference |
| `transport_adapter.adapter_id` | always | transport adapter identifier | e.g. `"sam"` |
| `transport_adapter.source_revision` | always | transport adapter source revision | explicit `"unavailable"` when no real source pin exists (see section 6) |
| `decision_ref` | when one exists | policy/decision reference | Option A: a reference only, never a verdict |
| `delegation_ref` | when supplied | parent/delegation/lineage reference | Option A extended: a reference only, never a grant |
| `execution_outcome` | always | execution outcome enum | closed enum, section 5 |
| `returned_payload_digest` | always | returned payload digest or `unavailable` | `sha256:<hex>` or literal `"unavailable"` |
| `error_code` | when applicable | error/refusal observation | short closed-vocabulary code, never raw error text |
| `error_observation_digest` | when an observation exists | error/refusal observation | `sha256:<hex>` digest of the raw observation bytes; omitted (not fabricated) when nothing was actually observed, e.g. a timeout |
| `unrecognized_input_fields` | when present | "unknown fields do not silently acquire meaning" | sorted list of input field **names only**, never values |
| `artifact_hashes` | always | cryptographic input-byte binding | `{"input/<file>": "sha256:<hex>"}`, whole-file binding of the explicit SAM observation input |

Receipts are **metadata-only**: raw arguments, raw payloads, and raw
error/refusal text are never carried. Every content reference is a
`sha256:` digest or an explicit `"unavailable"`/absence.

5. `execution_outcome` -- closed enum
----------------------------------------

| value | meaning | `returned_payload_digest` |
|---|---|---|
| `success` | the call executed and produced a payload | `sha256:<hex>` of the payload |
| `refused` | policy refused the call before any execution | literal `"unavailable"` |
| `transport_failure` | the call was admitted but the transport never returned a response | literal `"unavailable"` |
| `contaminated_response` | the call was admitted and a response frame arrived, but it failed the transport's own integrity check | literal `"unavailable"` (suspect bytes are pointed to only via `error_observation_digest`, a forensic pointer, never promoted to a trusted payload) |

A non-`success` outcome carrying a `sha256:` `returned_payload_digest` is
rejected by the verifier (`FABRICATED_NON_SUCCESS_PAYLOAD`). This is what
makes refusal and transport failure **valid, non-success receipts** rather
than receipts silently rewritten as fake successes.

6. Transport adapter identity and source pin
-----------------------------------------------

`transport_adapter.adapter_id` names the transport (`"sam"` for this lane).
`transport_adapter.source_revision` is meant to pin the specific transport
implementation a receipt was produced against. **At authoring time, a
repo-wide search of this repository and every sibling GARP/ARCS/DAGR repo
present on disk found no live "SAM" transport implementation anywhere.**
Per the dispatch lane's STOP condition ("STOP if a required field cannot be
observed from current SAM/DAGR-MCP surfaces; mark it unresolved rather than
fabricating it"), `source_revision` is carried as the explicit literal
string `"unavailable"` in every fixture in this pack. This is recorded as an
open item in `PROVENANCE.json` (`dispatch.unresolved_fields`), not silently
assumed resolved. It does not block the pack: every existing conformance
pack in this repository (`mcp-audit-trail`, `bedrock-openai-audit`) is
built the same way, from explicit, synthetic, non-live input.

7. Canonicalization rules
----------------------------

Two distinct serializations exist for two distinct purposes:

- **On-disk fixture format** (`tools/build_receipt.py` output): `json.dumps(
  receipt, indent=2, sort_keys=True) + "\n"`. This is what makes
  `tools/build_receipt.py` regenerate byte-identical fixtures from the same
  input -- deterministic, human-diffable, and what `check.sh` diffs against.
- **Canonical receipt identity** (`tools/verify_standalone.py
  .canonical_bytes` / `.receipt_identity_digest`): `json.dumps(receipt,
  sort_keys=True, separators=(",", ":"))`, sha256-hashed and reported as
  `sha256:<hex>`. `sort_keys=True` recursively sorts every object's keys at
  every nesting level, and the compact separators remove whitespace
  variance, so **any two JSON documents that encode the same value serialize
  to identical canonical bytes, regardless of on-disk field order**. This is
  the digest the acceptance gate "reordering JSON fields does not change
  canonical receipt identity" refers to; it is exercised in
  `tools/test_verify_standalone.py` against a hand-reordered copy of a valid
  receipt.

Determinism rules for individual fields:

- **Timestamps** (`requested_at`, envelope `issued_at`) are RFC 3339 UTC,
  second precision, with a literal `Z` suffix. Both are taken verbatim from
  the explicit input file -- never from the wall clock -- so regenerating a
  receipt from the same input is byte-identical.
- **Digests** are always `sha256:` followed by 64 lowercase hex characters,
  or the literal string `"unavailable"`. No other sentinel or casing is
  used.
- **Adapter metadata** (`transport_adapter`) is passed through verbatim from
  the input; unknown/extra keys inside it are not currently supported (only
  `adapter_id` and `source_revision` are read) and would need a schema
  revision to extend, consistent with `unrecognized_input_fields` only
  covering *top-level* unknown input keys in v0.1.
- **Field ordering** is irrelevant to receipt identity (see above) but is
  fixed to alphabetical (`sort_keys=True`) for on-disk fixtures, so diffs
  stay small and reviewable.

8. Core non-equivalences
----------------------------

A valid receipt under this profile proves only that its structure is
internally valid and that its bound observations/digests verify under these
rules:

```
receipt_valid != action_authorized
receipt_valid != output_true
receipt_valid != output_evidence_supported
receipt_valid != admitted
receipt_valid != published
```

These five lines are carried verbatim inside every receipt's
`attestation_limits` array (not only asserted in documentation), and are
independently re-asserted by `tools/verify_standalone.py`'s "does not claim"
footer on every report it prints.

9. Security/adversarial posture
------------------------------------

The canonical envelope validator's guardrails (`TOP_LEVEL_BODY_VERDICT`, on
the fixed key set `verdict`/`admitted`/`refused`/`held`/`status`) do **not**
cover this profile's full adversarial surface: neither `verified` nor
`published` is in that key set, and the canonical validator never inspects
inside `extensions.garp.body` at all. This profile adds a **pack-local**
guardrail layer (`tools/verify_standalone.py:enforce_sam_guardrails`) that
rejects, at the top level: `verified`, `published`; and inside
`extensions.garp.body`: `verified`, `published`, `admitted`, `refused`,
`action_authorized`, `output_evidence_supported`, `evidence_supported`,
`delegated_scope`, `authority_grant`, `scope_grant`. Presence of any of
these keys is disqualifying regardless of value -- this body_kind carries
only references (`decision_ref`, `delegation_ref`), never verdicts or
grants. `packs/sam-execution-receipt/v0.1/fixtures/invalid/` ships one
fixture per injected key demonstrating that the canonical validator alone
accepts each one, and that this pack-local guardrail rejects all of them.

See `packs/sam-execution-receipt/v0.1/README.md` for the runnable
demonstration and `packs/sam-execution-receipt/v0.1/check.sh` for the full
conformance check.
