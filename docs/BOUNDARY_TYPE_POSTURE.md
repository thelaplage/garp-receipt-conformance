boundary_type posture (v0.1)
============================

Purpose
-------

This note settles one question before the vendor-neutral pack shape
(`packs/mcp-audit-trail/v0.1/`) is cloned into vendor-specific packs:

> Is `audit_trail_boundary` an accepted routing value, or should the pack use an
> existing governed `boundary_type`?

It records the decision so that vendor packs do not inherit an ambiguous routing
value.

What the canonical schema says
------------------------------

In the canonical ARCS SRS envelope schema vendored in this repo
(`schemas/srs-envelope/v0.1.0/srs-envelope.schema.json`, pinned digest
`e866eabf…d6b61`), `boundary_type` is declared as:

```json
"boundary_type": { "type": "string" }
```

It is an **open string**. There is **no `enum`**, and this repo carries **no
`boundary_type` registry** of any kind. The canonical schema treats
`boundary_type` as a free-form routing label and does not enumerate or govern
its allowed values.

Decision (ratification)
-----------------------

Because the canonical schema treats `boundary_type` as an open string:

1. **`audit_trail_boundary` is accepted by this conformance pack** as a valid
   `boundary_type`. Using it is **not** a schema violation — the schema admits
   any string. The vendor-neutral MCP audit-trail pack and any pack that
   instantiates its shape may carry this value.

2. **`audit_trail_boundary` is a pack-local descriptive routing label, NOT a
   canonical registry value.** This repo does **not** mint canonical
   `boundary_type` values. The canonical `boundary_type` lane — whether the set
   of values is ever closed into an enum or a registry — remains `arcs-srs`'s to
   define upstream. The value here only names *how this receipt routes* (an
   audit-trail custody record); it makes no claim to be blessed, governed, or
   canonical.

3. **Vendor packs reuse the same value verbatim** rather than inventing new
   per-vendor routing values. A Bedrock/OpenAI/AWS/Microsoft custody-audit pack
   that instantiates the neutral shape routes the same way the neutral audit
   trail does, so it carries the **same** `audit_trail_boundary` value and
   inherits this posture. This keeps routing unambiguous across packs.

Guard (so this does not silently drift)
---------------------------------------

`packs/mcp-audit-trail/v0.1/check.sh` includes a posture guard that asserts:

- the canonical schema still declares `boundary_type` as an open string with
  **no `enum`** — i.e. no canonical enum/registry has been introduced that would
  make `boundary_type` a governed, closed field; and
- the pack's valid receipt carries `boundary_type: "audit_trail_boundary"`.

The guard's job is to **fail loudly if the open-string posture ever changes**. If
`arcs-srs` later closes `boundary_type` into an enum or registry, the guard
trips, and this posture must be revisited: `audit_trail_boundary` must then
either be **ratified upstream into the canonical enum**, or each pack must adopt
an **already-governed `boundary_type` value**. Until that happens, the value
remains pack-local descriptive and is **not** canonical.

What this posture does NOT do
-----------------------------

- It does **not** mint, register, or canonicalize `audit_trail_boundary`.
- It does **not** change `receipt_type`, `body_kind`, or the Option A /
  `decision_ref` discipline.
- It does **not** assert truth, admission, custody, or compliance of anything a
  receipt carries; see `ATTESTATION_LIMITS.md`.
- It does **not** edit the canonical schema or validator.
