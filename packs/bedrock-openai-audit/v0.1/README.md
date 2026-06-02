Bedrock/OpenAI Custody/Audit Pack (v0.1)
========================================

Status: the first **vendor-specific** receipt-bearing pack in this repo. It
**instantiates the vendor-neutral pack shape proven by**
`packs/mcp-audit-trail/v0.1/`. It does **not** invent a new receipt or
conformance shape: it reuses the same canonical SRS envelope schema, the same
envelope invariants, the same Option A / `decision_ref` discipline, the same
`boundary_type` routing value, and the same deterministic adapter shape. It
differs only in its explicit, vendor-shaped input.

**This is NOT a live integration.** No AWS, OpenAI, or Bedrock API is called. No
account, ARN, region, endpoint, organization, or credential identifier appears.
No environment variable is read, no network is touched, no scanner is run. The
input is an explicit, public-safe, **synthetic** file; the adapter reads one file
and writes one file.

What this pack is
-----------------

It takes one **explicit, public-safe, synthetic** Bedrock/OpenAI
**model-invocation custody/audit input file** and builds one ARCS SRS
**envelope** receipt from it with a minimal, deterministic adapter. The receipt
carries the audit evidence as a GARP body under `extensions.garp.body`, and the
pack proves that the receipt validates against the canonical SRS envelope schema
already vendored/reconciled in this repo.

```
input/bedrock_openai_audit.input.json              explicit public-safe synthetic Bedrock/OpenAI custody/audit input
tools/build_receipt.py                             minimal deterministic input -> receipt adapter
fixtures/valid/bedrock_openai_audit.envelope.json  generated/expected valid SRS envelope receipt
fixtures/invalid/top_level_status_verdict.json     forbidden-drift fixture (rejected)
expected/valid/   expected/invalid/                byte-for-byte expected validator output
PROVENANCE.json                                    authorship + public-safety + Option A record
check.sh                                           the pack conformance check
```

Run it from the repository root:

```
bash packs/bedrock-openai-audit/v0.1/check.sh
```

The check regenerates the receipt from the input (deterministic, byte-identical),
verifies the receipt cryptographically binds the input bytes, validates the
receipt against the canonical SRS envelope schema (exit 0, output matches
`expected/valid/`), and confirms the forbidden-drift fixture is rejected by that
same canonical validator (exit 1, output matches `expected/invalid/`).

What it proves — and what it does not
-------------------------------------

The verifier/conformance check validates **structural and cryptographic
integrity only**:

- **structural**: the receipt is a well-formed ARCS SRS envelope under the
  canonical schema (`schemas/srs-envelope/v0.1.0/`, pinned digest
  `e866eabf…d6b61`), with all GARP body content under `extensions.garp.body`.
- **cryptographic**: the receipt binds the exact input bytes — the sha256 in
  `extensions.garp.body.artifact_hashes` equals the sha256 of the input file —
  and regenerates byte-identically from that input.

It does **not** prove truth. It does not assert that any recorded audit event is
true, that any model invocation was authorized, that any custody claim is
correct, or that any external system behaved as the trail describes. In
particular it makes **no claim about the content, correctness, or truth of any
model output, and verifies no model output**. It is **not** a compliance
certification. The receipt attests envelope form and input-byte integrity;
nothing more. The body's `attestation_limits` say the same thing inside the
receipt, and `model_output_verification` is listed in
`artifact_classes_excluded`.

Why this is public-safe (despite being vendor-specific)
-------------------------------------------------------

- It is **synthetic**: no AWS / OpenAI / Bedrock API was called. The trail
  records that requests and responses passed through a custody gateway; it does
  not reproduce any real session.
- It carries **no** account, ARN, region, endpoint, organization, or credential
  identifier. Provider model references are **synthetic placeholders**
  (`bedrock:model-family-a`, `openai:model-family-b`), not real model IDs.
- It is **explicit-file input only**: no scanner, no live credentials, no
  environment variables, no network calls, no mutation of any external system,
  no private corpus. The adapter reads one file and writes one file.
- The trail is **digest-only**: prompts and model outputs appear as sha256
  digests, never as raw payloads. That is what makes the sample public-safe.

Envelope shape (required invariants — identical to the neutral pack)
--------------------------------------------------------------------

- **No top-level `receipt_class`.** The envelope carries none.
- **`receipt_type` remains the family axis** and is in the closed enum; this
  pack uses `provenance` (a custody/audit trail is provenance over model
  invocations) — unchanged from the neutral pack.
- **`boundary_type` remains the top-level routing axis.** This pack uses
  `audit_trail_boundary`, the **pack-local descriptive routing label reused
  verbatim from `packs/mcp-audit-trail/v0.1/`**. It is **not** a newly-minted
  canonical `boundary_type`: the canonical `boundary_type` lane remains
  `arcs-srs`'s to define. This custody/audit trail routes the same way the
  neutral audit trail does, so it carries the **same** descriptive value rather
  than introducing a new one. (The schema treats `boundary_type` as an open
  string; see this repo's `boundary_type` posture note for the ratification that
  this value is accepted as pack-local descriptive and does not mint a canonical
  registry entry.)
- **GARP body content lives under `extensions.garp.body`**, named by `body_kind`
  (`bedrock_openai_custody_audit`). Hoisting any of it to the top level is
  rejected by the canonical validator (see `docs/BODY_KIND_EXTENSION_RULES.md`).

Option A / `decision_ref` (preserved)
-------------------------------------

This pack preserves **Option A** as recorded in **garp-ops PR #87** (R0/R1
Option A) and **garp-sdk PR #78** (admission receipt contract conformed to
Option A / `decision_ref`):

- Any decision/verdict semantics are carried as a **reference** —
  `extensions.garp.body.decision_ref` — and **never** as a body-level or
  top-level `verdict` / `status` / `disposition` / `decision` /
  `governance_state`.
- The valid receipt demonstrates the correct shape (a `decision_ref` in the
  body, no verdict anywhere).
- The forbidden-drift fixture (`fixtures/invalid/top_level_status_verdict.json`)
  hoists the gateway decision onto the envelope as a top-level `status` verdict
  — the **same drift class** as the neutral pack's invalid fixture. The
  canonical validator rejects it with `TOP_LEVEL_BODY_VERDICT`, proving the
  vendor-specific pack inherits the identical guardrail.

Relationship to the neutral pack
--------------------------------

`packs/mcp-audit-trail/v0.1/` is the neutral pack that proved the shape. This
pack is its first vendor-specific instantiation. The discipline is unchanged;
only the input is vendor-shaped (a Bedrock/OpenAI model-invocation custody/audit
trail) and the `body_kind` names that shape. No invariant above is weakened, and
no garp-sdk code is imported or vendored.
