SAM Execution-Receipt Pack (v0.1) -- dispatch lane SAM-EXECUTION-RECEIPT0
===========================================================================

Status: **DRAFT. Do not merge.** `AUTHORITY_MOVEMENT = 0`: this pack asserts,
grants, and enforces nothing; it only defines a portable receipt shape and a
verifier for it.

Mission
-------

Define and verify a **portable execution receipt** for a remote MCP tool
invocation carried over SAM, without treating transport authentication or
successful execution as evidentiary truth, admission, or publication. SAM is
the *first* transport adapter this shape is proven for; the receipt shape
itself is transport-neutral, so a future transport can reuse it the same way
`packs/bedrock-openai-audit/v0.1/` reused the shape
`packs/mcp-audit-trail/v0.1/` proved.

**This is NOT a live integration.** A repo-wide search at authoring time found
no live "SAM" transport implementation anywhere in this repo or any sibling
GARP/ARCS/DAGR repo present on disk. No SAM/DAGR-MCP process is run, no
network is touched, no credentials are read to build or verify any receipt in
this pack. Every input file is an explicit, public-safe, **synthetic**
projection of what such a transport's observations would contain -- the same
explicit-file-only discipline already established by
`packs/mcp-audit-trail/v0.1/` and `packs/bedrock-openai-audit/v0.1/`.

What this pack is
------------------

```
input/sam_execution_success.input.json              admitted call, completed successfully
input/sam_execution_refused.input.json               policy refused before any execution
input/sam_execution_transport_failure.input.json     admitted, transport never returned a response
input/sam_execution_contaminated.input.json           admitted, response frame failed transport integrity check

tools/build_receipt.py            minimal deterministic SAM-observation -> receipt adapter
tools/verify_standalone.py        portable standalone verifier (single stdlib-only artifact)
tools/test_verify_standalone.py   parity + guard test (standalone vs canonical validator)

fixtures/valid/*.envelope.json        one generated receipt per execution_outcome (all four)
fixtures/invalid/top_level_status_verdict.json         canonical-drift fixture (rejected by the canonical validator)
fixtures/invalid/top_level_verified_true.json          standing-injection fixture (canonical-valid; SAM-guardrail-rejected)
fixtures/invalid/top_level_published_true.json         standing-injection fixture (canonical-valid; SAM-guardrail-rejected)
fixtures/invalid/body_admitted_true.json               standing-injection fixture (canonical-valid; SAM-guardrail-rejected)
fixtures/invalid/body_authority_grant.json             standing-injection fixture (canonical-valid; SAM-guardrail-rejected)
fixtures/invalid/body_evidence_support_injection.json  standing-injection fixture (canonical-valid; SAM-guardrail-rejected)

expected/valid/   expected/invalid/     byte-for-byte expected canonical-validator output
PROVENANCE.json                         authorship, public-safety, and per-artifact sha256 record
check.sh                                the pack conformance check
```

See `docs/SAM_EXECUTION_RECEIPT_V0_1.md` (repository root `docs/`) for the
full field-by-field schema, the canonicalization rule, and the required-vs-
optional field table.

Run it from the repository root:

```
bash packs/sam-execution-receipt/v0.1/check.sh
```

Integration seam: extends, does not invent
--------------------------------------------

This pack does **not** invent a new top-level receipt family. The canonical
SRS envelope schema (`schemas/srs-envelope/v0.1.0/`) already declares a
closed `receipt_type` enum: `sdk_enforcement`, `grace_session`, `connection`,
`provenance`. `sdk_enforcement` is the existing family for SDK/transport-
binding enforcement decisions over a tool call -- exactly what an execution
receipt over a new transport adapter is. This pack **extends** that family
with a new GARP body_kind, `sam_execution_receipt`, carried under
`extensions.garp.body`, and routes on the `boundary_type` value
`sdk_enforcement_boundary` (already seeded as the illustrative value for this
receipt_type in `fixtures/valid/sdk_enforcement.minimal.json`, but not
previously used by any pack; this is the first pack to route on it -- see
`docs/BOUNDARY_TYPE_LEDGER.md`).

Why a pack-local verifier layer is necessary
----------------------------------------------

The canonical envelope validator (`tools/validate_srs_envelope.py`) rejects a
fixed, small set of top-level keys as body verdicts: `verdict`, `admitted`,
`refused`, `held`, `status`. It has no notion of `sam_execution_receipt`
body-kind semantics and **never inspects inside `extensions.garp.body` at
all**. That means:

- a top-level `verified: true` or `published: true` injection is **not**
  caught by the canonical validator (neither key is in its guardrail list),
- a body-level `admitted: true`, `output_evidence_supported: true`, or
  `delegated_scope: "full_access"` injection is **not** caught either (the
  canonical validator only looks at top-level keys).

`fixtures/invalid/top_level_verified_true.json`,
`top_level_published_true.json`, `body_admitted_true.json`,
`body_authority_grant.json`, and `body_evidence_support_injection.json` each
demonstrate this directly: **all five pass the canonical envelope
validator.** `check.sh` asserts this explicitly (step 7) so the gap stays
documented rather than silently assumed. `tools/verify_standalone.py` adds a
pack-local **SAM standing-injection guardrail** on top of (never in place of)
the canonical checks, and rejects all five. This is the concrete answer to
the dispatch lane's adversarial requirement: *"reject attempts to inject or
infer `verified=true`, `published=true`, `admitted=true`, evidence/support
standing not present in licensed upstream contracts, [or] broader delegated
authority than the decision/delegation reference licenses."*

`fixtures/invalid/top_level_status_verdict.json` is the one fixture in this
pack that **is** rejected by the canonical validator itself
(`TOP_LEVEL_BODY_VERDICT`) -- the same drift class every other pack in this
repo demonstrates, included here so this pack's conformance suite still
proves that layer too.

Core non-equivalences
----------------------

A valid receipt from this pack proves only that its structure is internally
valid and that its bound observations/digests verify under the stated
conformance rules. It never proves:

- `receipt_valid != action_authorized`
- `receipt_valid != output_true`
- `receipt_valid != output_evidence_supported`
- `receipt_valid != admitted`
- `receipt_valid != published`

These five lines are carried verbatim inside every receipt's
`attestation_limits` array, not only asserted in this README.

Refusal and transport failure are valid receipts, not fake success
----------------------------------------------------------------------

`execution_outcome` is a closed enum: `success`, `refused`,
`transport_failure`, `contaminated_response`. A refusal or a transport
failure produces a structurally **valid** SRS envelope receipt whose
`returned_payload_digest` is the literal string `"unavailable"` -- never a
fabricated success payload. `tools/verify_standalone.py` enforces this
directly (`FABRICATED_NON_SUCCESS_PAYLOAD`): any non-success outcome carrying
a `sha256:` returned-payload digest fails verification. A
`contaminated_response` outcome records that the returned bytes failed the
transport's own integrity check; the suspect bytes are pointed to only by a
forensic `error_observation_digest`, never promoted to a trusted
`returned_payload_digest`, and no claim is made about their content.

Deterministic receipt identity, reordering-stable
-----------------------------------------------------

`tools/verify_standalone.py` computes a receipt identity digest over a
canonical serialization (`json.dumps(receipt, sort_keys=True,
separators=(",", ":"))`, sha256). Because `sort_keys=True` recursively sorts
every object's keys, two on-disk JSON documents that encode the same value --
regardless of top-level or nested field order -- produce the **identical**
identity digest. `tools/test_verify_standalone.py` proves this against a
hand-reordered copy of a valid receipt (check: "canonical receipt identity is
invariant under field reordering").

Mutated bound digests invalidate the receipt
-----------------------------------------------

Beyond the whole-file `artifact_hashes` binding (present in every pack in
this repo), this pack's verifier additionally cross-checks the receipt's own
`canonical_arguments_digest`, `returned_payload_digest`, and
`error_observation_digest` fields against what the explicit SAM observation
input file declares. `tools/test_verify_standalone.py` demonstrates that
mutating either digest away from the input's declared value makes
`check_input_binding` fail -- a mismatched receipt is invalid, not silently
accepted.

Unknown SAM fields never silently acquire meaning
------------------------------------------------------

`tools/build_receipt.py` maps only a fixed, documented set of known SAM
observation fields. Any top-level input field the adapter does not recognize
is listed by **name only** (never its value) under
`extensions.garp.body.unrecognized_input_fields`.
`input/sam_execution_contaminated.input.json` carries one intentionally
unrecognized field, `vendor_experimental_flag`, to exercise this: it appears
only as a bare name in `unrecognized_input_fields`, and nowhere else in the
receipt.

Distinguishing caller / transport / service / content identity
--------------------------------------------------------------------

Each identity axis is a separately named field, never conflated:

- caller identity -- `caller_ref`
- transport identity -- `transport_session_ref` and `transport_adapter`
  (`adapter_id` + `source_revision`)
- service/node identity -- `target_ref`
- content/artifact identity -- `canonical_arguments_digest`,
  `returned_payload_digest`, `artifact_hashes`

What it proves -- and what it does not
------------------------------------------

**Structural + cryptographic only, exactly as for every other pack in this
repo:**

- **structural**: the receipt is a well-formed ARCS SRS envelope under the
  canonical schema (`schemas/srs-envelope/v0.1.0/`, pinned digest
  `e866eabf…d6b61`), with all GARP body content under
  `extensions.garp.body`, and it satisfies the pack-local SAM standing-
  injection guardrail described above.
- **cryptographic**: `artifact_hashes` binds the exact input bytes, and the
  receipt's own bound digest fields match what the input file declares.

It does **not** prove truth, authorization, evidentiary standing, admission,
or publication of anything a receipt carries. It independently
**recomputes** structure and bindings; it never re-asserts the emitter's own
claims as if they were a finding on their own (emitter assertion !=
independently-recomputed finding). `boundary_type` stays descriptive: the
verifier does not route on it.

Unresolved / STOP-relevant items
------------------------------------

- No live SAM transport implementation exists anywhere in this repo or any
  sibling GARP/ARCS/DAGR repo checked at authoring time. Per the dispatch
  lane's STOP condition ("STOP if a required field cannot be observed from
  current SAM/DAGR-MCP surfaces; mark it unresolved rather than fabricating
  it"), `transport_adapter.source_revision` is carried as the explicit
  literal `"unavailable"` in every fixture rather than a fabricated commit
  pin. This is not treated as a blocking STOP because it matches the
  established, sanctioned pattern of every existing pack in this repo:
  explicit-file, synthetic, non-live-integration input.
