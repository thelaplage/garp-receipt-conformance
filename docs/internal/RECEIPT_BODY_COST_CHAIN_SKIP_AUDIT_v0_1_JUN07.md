Receipt Body Cost, Chain, and Skip Audit v0.1
=============================================

§0 Metadata
-----------

- status: internal_audit_v0_1
- source overlap: Reactor/OpenProse receipt and cost model audit
- scope: receipt-conformance / SRS envelope / external verifier portability
- non-goal: immediate schema mutation

Read scope: `README.md`; `schemas/srs-envelope/v0.1.0/`; the canonical
validator; root and pack fixtures; body-kind, schema, validator, fixture,
boundary_type, attestation, and standalone verifier docs; the MCP and
Bedrock/OpenAI pack adapters, checks, and verifier guard.

§1 Executive finding
--------------------

Token attribution is partially present only for provider/model provenance in
the Bedrock/OpenAI pack body events. Token accounting is absent. There is no
`tokens.fresh`, `tokens.reused`, or `surprise_cause` / wake source contract.
The lift is an absent/candidate body extension, not an envelope field.

Chain identity is partial. The repo verifies the canonical schema digest and
pack-specific explicit input bytes via `extensions.garp.body.artifact_hashes`,
but it does not carry receipt-level `hash_algorithm`, receipt `content_hash`,
canonical receipt-byte hash, or a `prev pointer`. Chain verification is partial
to absent and must attach to the existing `srs_receipt_external_verifier.py`
standalone-portability backlog item.

Skipped/no-op receipts are absent. The current envelope rejects top-level
`status` as a body-verdict discriminator, and current packs preserve
`decision_ref` instead of verdict/status fields. A cheap no-op receipt is a
candidate body-kind extension only, not a new status, not a new
AdmissionDecision, and not a backdoor admission state.

§2 Token attribution audit
--------------------------

| Concept | Current support | Location if present | Gap | Recommendation |
| --- | --- | --- | --- | --- |
| provider/model | Partially present. The Bedrock/OpenAI pack records `provider`, `model_ref`, and `providers` in its synthetic custody audit body. Root fixtures and the neutral MCP pack do not carry model attribution. | `packs/bedrock-openai-audit/v0.1/fixtures/valid/bedrock_openai_audit.envelope.json` under `extensions.garp.body.events[]` and `extensions.garp.body.providers`. | This is pack-specific provenance, not a general receipt-body cost contract and not an AdmissionReceiptBody or RefusalReceiptBody field in this repo. | No schema mutation. If generalized, use a registered body_kind under `extensions.garp.body` if that is the repo convention. |
| tokens.fresh | Absent. | Not present. | No current receipt body accounts for fresh token spend. | Candidate extension through body_kind semantics, not a canonical envelope field. |
| tokens.reused | Absent. | Not present. | No current receipt body separates reused or cached tokens from fresh tokens. | Candidate extension through body_kind semantics, paired with `tokens.fresh` so FSI review can distinguish external movement from reused context. |
| surprise_cause / wake source | Absent. | Not present. | No receipt records why work woke, what external input moved, or what caused surprise. | Candidate extension through body_kind semantics. Keep it as provenance/evidence, not a decision field. |
| body_kind extension path | Present as a location rule, not as a local registry. GARP body content belongs under `extensions.garp.body` and is named by `body_kind`. | `docs/BODY_KIND_EXTENSION_RULES.md`; pack bodies under `extensions.garp.body.body_kind`. | This conformance repo defines no body-kind schema registry and blesses no GARP body semantics. | Any future token-cost body must be registered upstream or through the existing body_kind / extensions.garp.body path if that is the repo convention. |
| FSI audit value | Absent for token spend, partially present for provider/model provenance. | Provider/model only in the Bedrock/OpenAI pack body. | A reviewer cannot currently prove from a receipt that token spend was caused by external input movement rather than background clock-cycle work. | Candidate extension. Record provider/model, `tokens.fresh`, `tokens.reused`, and wake source in a body_kind, without changing the canonical envelope. |

§3 Chain identity audit
-----------------------

| Concept | Current support | Location if present | Gap | Recommendation |
| --- | --- | --- | --- | --- |
| hash_algorithm | Partial. The schema manifest records SHA-256 for the schema, and artifact hashes use `sha256:` prefixes. There is no receipt-level `hash_algorithm` field. | `schemas/srs-envelope/v0.1.0/srs-envelope.schema.manifest.json`; `extensions.garp.body.artifact_hashes` in fixtures and packs. | Algorithm identity is implicit or pack-specific for artifacts, not explicit for receipt content identity. | Attach to the existing `srs_receipt_external_verifier.py` standalone-portability backlog item. Do not create a parallel workstream. |
| content_hash | Absent as receipt identity. `artifact_hashes` bind input artifacts, not the receipt envelope bytes. | Not present as `content_hash`; artifact input hashes live under `extensions.garp.body.artifact_hashes`. | An external verifier cannot read a receipt's own content hash from the receipt. | Attach to the existing `srs_receipt_external_verifier.py` standalone-portability backlog item. Do not create a parallel workstream. |
| canonical byte hash | Partial to absent. Validators hash schema bytes and pack checks compare deterministic generated receipt bytes, but no receipt field states a hash over canonical receipt bytes. | `tools/validate_srs_envelope.py` schema digest gate; pack `check.sh` deterministic regeneration checks. | No canonical receipt-byte hashing contract is exposed in the envelope or body. | Attach to the existing `srs_receipt_external_verifier.py` standalone-portability backlog item. Do not create a parallel workstream. |
| prev pointer | Absent. No `body.prev`, prior receipt reference, or prior envelope content hash appears in valid fixtures or pack bodies. | Not present. | Receipt chains cannot be followed or checked from current receipt bytes. | Attach to the existing `srs_receipt_external_verifier.py` standalone-portability backlog item. Do not create a parallel workstream. |
| chain consistency verifier | Absent. Existing validators verify envelope form, schema identity, and pack input-byte binding, not chain consistency. | `tools/validate_srs_envelope.py`; `packs/bedrock-openai-audit/v0.1/tools/verify_standalone.py`. | No verifier checks that one receipt links to the prior receipt content hash. | Attach to the existing `srs_receipt_external_verifier.py` standalone-portability backlog item. Do not create a parallel workstream. |
| external verifier from bytes alone | Partial. The verifier can validate receipt JSON form from receipt bytes plus schema assets. The Bedrock/OpenAI standalone verifier also requires explicit input bytes for artifact binding. | `packs/bedrock-openai-audit/v0.1/tools/verify_standalone.py`. | It cannot validate receipt self-identity or chain consistency from receipt bytes alone because `content_hash` and `prev pointer` are absent. | Attach to the existing `srs_receipt_external_verifier.py` standalone-portability backlog item. Do not create a parallel workstream. |
| srs_receipt_external_verifier.py standalone portability | Existing backlog target named by this audit, but the file is not present in this repo. Local verifier portability is represented by the Bedrock/OpenAI standalone verifier and parity guard. | `packs/bedrock-openai-audit/v0.1/tools/verify_standalone.py`; `packs/bedrock-openai-audit/v0.1/tools/test_verify_standalone.py`. | The named backlog item must absorb chain identity if adopted. | Chain identity recommendations in this memo attach to the existing `srs_receipt_external_verifier.py` standalone-portability backlog item. Do not create a parallel workstream. |

§4 Skipped/no-op receipt audit
------------------------------

| Concept | Current support | Location if present | Gap | Recommendation |
| --- | --- | --- | --- | --- |
| skipped/no-op status | Absent, and top-level `status` is explicitly rejected when used as a body verdict. | Rejection rule in `tools/validate_srs_envelope.py`; drift fixtures in root, MCP, and Bedrock/OpenAI packs. | No valid skipped/no-op status exists. | Do not add status. If needed, model as a body_kind extension under `extensions.garp.body`. |
| unchanged-input receipt | Absent. | Not present. | The repo does not show unchanged-input admission cycles, so it does not prove whether such cycles are receipted or silent in a runtime. | Candidate cheap receipt body_kind for audit completeness, preserving input identity and no-action evidence. |
| cheap no-op receipt | Absent. | Not present. | No minimal receipt records an unchanged input or no admission action. | Candidate extension. Keep it cheap and evidence-only, with no canonical envelope mutation. |
| interaction with AdmissionDecision | No AdmissionDecision contract is defined in this conformance repo; pack docs preserve Option A by carrying `decision_ref` only. | `extensions.garp.body.decision_ref` in MCP and Bedrock/OpenAI packs. | A skipped/no-op concept could become a hidden admission state if encoded as a decision enum. | This audit does not add new AdmissionDecision values. Use `decision_ref` or body evidence only, if needed. |
| interaction with RefusalReceiptBody | No RefusalReceiptBody contract is defined in this conformance repo. Root compression disposition has `refused_candidates`, but that is body detail only. | `fixtures/valid/compression_disposition.envelope.json` under `extensions.garp.body.refused_candidates`. | No contract distinguishes skipped from refusal. | Do not overload refusal. If adopted, skipped/no-op should be its own body_kind or body posture, not a refusal verdict. |
| audit completeness value | Absent in current receipts. | Not present. | Silent no-ops would leave no receipt-level evidence that inputs did not move or that no admission action occurred. | Candidate extension for a cheap no-op receipt, with cache keys based only on input identity. |

§5 Decision posture
-------------------

| Lift | Outcome | Note |
| --- | --- | --- |
| Token attribution | candidate extension: attach to external-verifier portability workstream | Provider/model appears in one pack-specific body, but the token-cost lift is absent. Keep future work under body_kind / extensions.garp.body if that is the repo convention. |
| Chain identity | candidate extension: attach to external-verifier portability workstream | Chain identity is partial to absent. The recommendation attaches to the existing `srs_receipt_external_verifier.py` standalone-portability backlog item. |
| Skipped/no-op receipt | candidate extension: attach to external-verifier portability workstream | Do not express skipped/no-op as status or AdmissionDecision. Treat it as a possible cheap receipt body_kind only if adopted. |

§6 Guardrails
-------------

- This audit does not introduce new substrate vocabulary.
- This audit does not add new AdmissionDecision values.
- This audit does not add receipt fields.
- Any future extension must be registered through the existing body_kind / extensions.garp.body path if that is the repo convention.
- Cache keys, if discussed, must be input identity only, never decisions.
- Cache keys are input identity only, never the decision.
- This rule is recorded after OpenProse's `delta.md` documented retirement of a prior memo key that included verdict/policy fields and became a hidden policy surface.
- A skipped/no-op receipt must not become a backdoor admission status.
