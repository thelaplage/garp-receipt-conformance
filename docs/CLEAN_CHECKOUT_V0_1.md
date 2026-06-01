Clean-Checkout Verification v0.1
================================

Status: first public clean-checkout verification (Stage C5).

This document describes `scripts/check_pack_v0_1.sh`, the single command that
lets an outside verifier confirm the receipt envelope conformance pack v0.1 is
self-contained and behaves as committed — runnable from a clean public checkout
with nothing more than a stock Python 3 interpreter and standard POSIX tooling.

1. How an external verifier runs the pack
-----------------------------------------

From a clean checkout, at the repository root:

```
git clone <this-repo-url> garp-receipt-conformance
cd garp-receipt-conformance
bash scripts/check_pack_v0_1.sh
```

No `pip install`, no lockfile, no network access, and no access to any private
repository or private corpus is required or performed. The script must be run
from the repository root; it refuses to run elsewhere (exit `2`) so that the
relative artifact paths it checks are unambiguous.

The script fails fast: the first failing check aborts the run with a non-zero
exit status. A fully successful run exits `0` and ends with a single summary
line:

```
PASS: receipt-envelope conformance pack v0.1 (7 checks)
```

2. What the script checks
-------------------------

In order, fail-fast:

1. `git diff --check` — the working tree carries no whitespace errors or
   unresolved merge-conflict markers.
2. `python3 -m json.tool` on the schema artifact
   (`schemas/receipt-envelope-v0.1.schema.json`) — it parses as JSON.
3. `python3 -m json.tool` on the valid fixture
   (`fixtures/valid/receipt-envelope-minimal-v0.1.json`) — it parses as JSON.
4. `python3 -m json.tool` on the invalid fixture
   (`fixtures/invalid/receipt-envelope-missing-body-v0.1.json`) — it parses as
   JSON. (Invalid here means envelope-form-invalid, not malformed JSON.)
5. `shasum -c schemas/receipt-envelope-v0.1.sha256` — the schema artifact
   matches its pinned digest.
6. The valid fixture run through
   `validator/validate_receipt_envelope_v0_1.py` exits `0` and its stdout
   matches `expected/valid-receipt-envelope-minimal-v0.1.txt` byte-for-byte
   (`diff -u`).
7. The invalid fixture run through the same validator exits `1` and its stdout
   matches `expected/invalid-receipt-envelope-missing-body-v0.1.txt`
   byte-for-byte (`diff -u`).

The validator and `json.tool` invocations use only the Python 3 standard
library. The script writes captured validator output to a private temporary
directory created with `mktemp -d` and removes it on exit (including on error
or interrupt). Output is deterministic and concise: one `ok N - …` line per
passed check, then the summary line.

3. What success means
---------------------

A `PASS` result means, for this clean checkout:

- The committed JSON artifacts are well-formed JSON.
- The schema artifact still matches its pinned digest (it has not drifted).
- The committed local validator, run against the committed fixtures, produces
  exactly the committed pass/fail exit codes and output.
- The pack is internally consistent and reproducible end-to-end with no
  network, no installed dependencies, and no private inputs.

In short: the public envelope-form contract, fixtures, expected outputs, and
validator agree with each other and are verifiable by anyone, from scratch.

4. What success does NOT mean
-----------------------------

A `PASS` does not establish any of the following:

- It does not prove the truth, correctness, legal compliance, security, or
  performance of anything a receipt describes.
- It does not validate `body` contents or perform any `body_kind`-specific
  schema validation; the envelope `body` is opaque at this layer (see
  `docs/BODY_KIND_EXTENSION_RULES.md`).
- It does not assert that any product or runtime emitted, or would emit, a
  conforming receipt. The script inspects committed fixtures only.
- It does not claim or imply external adoption.
- It does not retire, satisfy, or substitute for any real external artifact
  gate; it verifies only the public fixtures and validator in this pack.

See `docs/ATTESTATION_LIMITS.md` for the full attestation-limit policy.

5. No-private-corpus rule
-------------------------

Per `docs/NO_PRIVATE_CORPUS.md`, the pack must be runnable from a clean public
checkout without access to private corpus material, operator-local records,
private stores, or Vega Commons internal repositories. This verification script
honors that rule: every input it reads is a public artifact committed to this
repository, and it performs no network access and no dependency install. A
verification result that depended on private corpus access would not be an
external conformance result.

6. Non-claims
-------------

This verification script and this document make none of the following claims:

- No product/runtime receipt is emitted. The script only re-runs the public
  validator over committed fixtures; it does not produce receipts.
- No external adoption is claimed or implied.
- No `body_kind`-specific validation is performed.
- No proof of truth, correctness, compliance, security, or performance is
  provided.
- No dependency on any private repository or private corpus exists.
- No real external artifact gate is retired or satisfied by a passing run.
