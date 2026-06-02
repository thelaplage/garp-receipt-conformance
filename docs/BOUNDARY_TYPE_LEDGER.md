boundary_type value ledger (conformance-repo)
=============================================

Purpose
-------

This is the single conformance-repo ledger of the `boundary_type` values used by
packs in this repository. It exists to **centralize honesty** about open-string
`boundary_type` values so that, as more packs land, pack-local descriptive values
do not sprawl undocumented.

It complements `docs/BOUNDARY_TYPE_POSTURE.md`, which ratifies *why*
`boundary_type` is treated as an open string and *why* a value used by a pack is
pack-local descriptive rather than canonical. This file is the *register* of the
actual values in use, so the honesty lives in one place instead of being
scattered across pack READMEs and `PROVENANCE.json` files.

Scope and non-claim
-------------------

- This ledger **records and classifies** `boundary_type` values; it does **not**
  mint, register, govern, or canonicalize any value. Listing a value here makes
  it traceable, not blessed.
- The canonical schema
  (`schemas/srs-envelope/v0.1.0/srs-envelope.schema.json`) declares
  `boundary_type` as an **open string** (no `enum`, no registry). The canonical
  `boundary_type` lane — whether its values are ever closed into an enum or a
  registry — remains `arcs-srs`'s to define upstream. This ledger does not
  change that.
- The external verifier **does not route on `boundary_type`.** It routes on the
  canonical axes — `receipt_type`, `body_kind`, and schema invariants.
  `boundary_type` is descriptive top-level context only. The risk this ledger
  addresses is **not** schema failure; it is undocumented open-string value
  sprawl.

Classification vocabulary
-------------------------

Each value is classified as exactly one of:

- **canonical** — only if ratified upstream **outside this repo** (in
  `arcs-srs`). This repo never assigns this class on its own authority.
- **pack-local descriptive** — used by a pack under the open-string posture; not
  canonical. Names only *how a receipt routes*, with no claim to be governed.
- **deprecated/replaced** — a value previously used that has since been changed;
  retained here for traceability with a pointer to its replacement.

Ledger
------

### `audit_trail_boundary`

- **classification:** pack-local descriptive
- **canonical_status:** not canonical
- **route_authority:** the verifier does **not** route on this value; the
  verifier routes on `receipt_type` / `body_kind` / schema invariants.
  `boundary_type` is descriptive top-level context.
- **used_by:**
  - `packs/mcp-audit-trail/v0.1/`
  - `packs/bedrock-openai-audit/v0.1/`
- **source PRs:**
  - #8 / `72e3a18` — ratified `audit_trail_boundary` as pack-local descriptive
    under the open-string posture (see `docs/BOUNDARY_TYPE_POSTURE.md`).
  - #9 / `bf5ca67` — first vendor-specific instantiation
    (`packs/bedrock-openai-audit/v0.1/`) reusing the value verbatim.
- **notes:** the Bedrock/OpenAI pack reuses this value verbatim rather than
  inventing a per-vendor routing value: a custody/audit trail routes the same way
  the neutral audit trail does, so it carries the same descriptive value.

Rule for future packs
---------------------

Every new `boundary_type` value introduced by a pack **must be added to this
ledger**, or the pack must **consciously reuse an existing pack-local descriptive
value** already recorded here (and say so, as `packs/bedrock-openai-audit/v0.1/`
does for `audit_trail_boundary`). A pack may not introduce an undocumented
open-string `boundary_type` value.

Adding a value here records and classifies it; it does **not** mint a canonical
value. A value may only be classified **canonical** if it is ratified upstream
outside this repo; until then it is **pack-local descriptive**. If a value is
later changed, reclassify the old value as **deprecated/replaced** and point to
its replacement rather than deleting the row.
