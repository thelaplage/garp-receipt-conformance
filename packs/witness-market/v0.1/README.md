Witness-Market Pack (v0.1)
===========================

Status: DRAFT. `AUTHORITY_MOVEMENT: 0`. See `docs/dispatch/WITNESS-MARKET0.md`.

What this pack is
------------------

Receipt verification/witness/storage/replay capabilities are discoverable
**market** capabilities, without truth or authority effect. It takes one
**explicit, public-safe** witness-market scenario — a provider's
`WitnessServiceOffer` (for `receipt_verify`, `receipt_witness`, `receipt_store`,
or `replay_verify`), a `WitnessRequest` that binds that offer to the exact
digest of a receipt someone wants observed, and the `WitnessResult` the
provider returns — and builds one ARCS SRS **envelope** receipt from it with a
minimal, deterministic adapter. The receipt carries the market-transaction
record as a GARP body under `extensions.garp.body`, and the pack proves that
receipt validates against the canonical SRS envelope schema already
vendored/reconciled in this repo.

```
input/witness_market.input.json     explicit public-safe witness-market scenario
tools/build_receipt.py              minimal deterministic input -> receipt adapter
tools/check_invariant_guard.py      exercises witness_market.py's own invariants
fixtures/valid/witness_market.envelope.json    generated/expected valid SRS envelope receipt
fixtures/invalid/top_level_status_verdict.json forbidden-drift fixture (rejected)
expected/valid/   expected/invalid/  byte-for-byte expected validator output
PROVENANCE.json                      authorship + public-safety record
check.sh                             the pack conformance check
```

Run it from the repository root:

```
bash packs/witness-market/v0.1/check.sh
```

The check regenerates the receipt from the input (deterministic,
byte-identical), verifies the receipt cryptographically binds the input bytes,
validates the receipt against the canonical SRS envelope schema (exit 0,
output matches `expected/valid/`), confirms the forbidden-drift fixture is
rejected by that same canonical validator (exit 1, output matches
`expected/invalid/`), and runs the invariant guard against `witness_market.py`
(repository root) directly.

Required invariant
-------------------

```
witness_offer_exists != witness_selected != receipt_observed
    != receipt_valid != action_authorized != result_true
```

A witness offer existing does not mean it was selected. A witness being
selected does not mean a receipt was observed. A receipt being observed does
not mean it is valid. A receipt being valid does not mean the action it
describes was authorized. None of the above means the underlying result is
true. **Witness count never substitutes for verification or admission** —
observing (or storing, or replaying) a receipt many times over does not make
its contents true, does not authorize anything, and does not admit anything.

This is enforced two ways:

- **In the contracts** (`witness_market.py`, repository root):
  `WitnessServiceOffer`, `WitnessRequest`, and `WitnessResult` structurally
  **lack** any `authority_effect` or `truth_effect` field — non-authority is
  expressed by the field's absence, never by a field pinned to `"none"`.
  `WitnessServiceOffer.build` raises `ValueError` if any guarantee tries to
  promise `truth`, `authorized`, `admitted`, `trusted`, or `standing`, and
  `witness_market.reject_authority_injection` fails closed (raises
  `ValueError`) if untrusted scenario input tries to smuggle an
  authority/truth/admission-shaped key in at all.
- **In the receipt shape**: the market transaction's `result.status` field
  (`PASS` / `FAIL` / `NOT_EVALUATED` / `OBSERVED`) lives only under
  `extensions.garp.body.result.status`. Hoisting it to a top-level `status` on
  the envelope — asserting the witness result as an envelope-level verdict —
  is exactly what `fixtures/invalid/top_level_status_verdict.json` does, and
  the canonical validator rejects it with `TOP_LEVEL_BODY_VERDICT`.

What this pack proves — and what it does not
----------------------------------------------

The verifier/conformance check validates **structural and cryptographic
integrity only**, plus the market layer's own non-collapse invariant:

- **structural**: the receipt is a well-formed ARCS SRS envelope under the
  canonical schema (`schemas/srs-envelope/v0.1.0/`, pinned digest
  `e866eabf…d6b61`), with all market-transaction detail under
  `extensions.garp.body`.
- **cryptographic**: the receipt binds the exact input bytes — the sha256 in
  `extensions.garp.body.artifact_hashes` equals the sha256 of the input file —
  and regenerates byte-identically from that input.
- **non-collapse**: the offer, request, and result identifiers stay distinct
  and bind correctly to one another (no silent substitution), and no
  `authority_effect`/`truth_effect` field is ever defined on the market
  contracts or serialized into the receipt body — structural absence, not a
  value pinned to `"none"`.

It does **not** prove that the subject receipt (`subject_ref`, the receipt
being witnessed) is valid. It does not prove that any action the subject
receipt describes was authorized. It does not prove that the witness
observation itself is true. A market transaction record is evidence that an
offer/request/result exchange happened in the shape this pack describes —
nothing more.

Why this is vendor-neutral
---------------------------

- The scenario is generic witness-market evidence: a generic provider node ID
  (`node:witness-alpha`), a generic profile ref, generic guarantees
  (`exact_bytes`, `observed_at`). There is no vendor identifier, no vendor
  profile, no account, ARN, region, or product name.
- It is **explicit-file input only**: no scanner, no live credentials, no
  network calls, no mutation of any external system, no private corpus. The
  adapter reads one file and writes one file.
- The subject receipt digest is a **synthetic placeholder** (the sha256 of a
  literal string documented in the input file), not a real receipt — the pack
  proves the market-transaction shape, not a claim about any specific receipt.

Envelope shape (required invariants)
--------------------------------------

- **No top-level `receipt_class`.** The envelope carries none.
- **`receipt_type` remains the family axis** and is in the closed enum; this
  pack uses `provenance` (a witness-market transaction is provenance over a
  receipt-observation request).
- **`boundary_type` remains the top-level routing axis.** This pack uses
  `witness_market_boundary`, a **pack-local descriptive routing label**. It is
  **not** a newly-minted canonical `boundary_type`: the canonical
  `boundary_type` lane remains `arcs-srs`'s to define. The canonical schema
  treats `boundary_type` as an **open string** (no enum, no registry), so this
  value is **accepted** by the conformance pack precisely because the field is
  open — it mints nothing canonical. `check.sh` carries a posture guard that
  fails loudly if that open-string posture ever changes.
- **GARP body content lives under `extensions.garp.body`**, named by
  `body_kind` (`witness_market_transaction`). Hoisting any of it to the top
  level is rejected by the canonical validator (see
  `docs/BODY_KIND_EXTENSION_RULES.md`).

Non-goals
---------

- This pack does not build a live witness marketplace, a discovery service, a
  payment/settlement layer, or any network-facing component. It is an
  explicit-file, offline conformance pack only.
- It does not define new `receipt_type` enum values, does not close
  `boundary_type` into an enum, and does not touch the canonical schema,
  manifest, or validator vendored at the repository root.
- It does not certify that any real provider node, receipt, or witness
  observation exists; every artifact here is synthetic and authored in this
  repository (see `PROVENANCE.json`).
