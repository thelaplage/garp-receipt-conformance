Provenance Rules
================

Status: every vendored artifact records byte-identical provenance against its
`arcs-srs` source.

This pack is a faithful vendoring of canonical artifacts from `arcs-srs`. To
make the copy auditable, every vendored file records provenance: where it came
from, the source bytes' digest, the copied bytes' digest, and that the two are
identical.

1. Provenance files
-------------------

- `schemas/srs-envelope/v0.1.0/PROVENANCE.json` — provenance for the schema, the
  schema manifest, and the validator (`tools/validate_srs_envelope.py`).
- `fixtures/PROVENANCE.json` — provenance for every fixture under
  `fixtures/valid/` and `fixtures/invalid/`.

2. Recorded fields
------------------

Each entry mirrors the `arcs-srs` `conformance/fixtures/PROVENANCE.json` pattern:

- `source_repo` — `arcs-srs` (the vendoring source of truth).
- `source_path` — path of the artifact within `arcs-srs`.
- `source_artifact_sha256` — SHA-256 of the source bytes.
- `copied_artifact_sha256` — SHA-256 of the vendored bytes in this pack.
- `copy_is_byte_identical` — `true`; the two digests are equal.

For `fixtures/valid/compression_disposition.envelope.json`, the entry also
records the upstream origin (`arcs-amnesiac`) that `arcs-srs` itself vendored
from, for traceability. The pack's vendoring source of truth remains `arcs-srs`.

3. The byte-identical rule
--------------------------

The pack copies canonical artifacts byte-identical and never edits, normalizes,
reformats, or improves them. Any quirk in the canonical artifacts — for example
`additionalProperties: true` or the `receipt_signature` shape — is preserved
exactly. If a canonical artifact needs a change, that change is made upstream in
`arcs-srs` first and then re-vendored; a normalization applied during vendoring
would be a new drift.

4. Verifying provenance from a clean checkout
---------------------------------------------

Each `copied_artifact_sha256` can be recomputed and compared against the
vendored bytes, e.g.:

    shasum -a 256 schemas/srs-envelope/v0.1.0/srs-envelope.schema.json
    shasum -a 256 fixtures/valid/provenance.minimal.json

The schema additionally carries `schemas/srs-envelope/v0.1.0/srs-envelope.schema.sha256`
for a direct `shasum -c` check, and the validator re-verifies the schema digest
against the manifest at runtime.

5. Public-safety posture
------------------------

All fixtures are validatable from a clean public checkout without private-corpus
access (see `NO_PRIVATE_CORPUS.md`). No fixture requires a private repository or
internal runtime state to validate.
