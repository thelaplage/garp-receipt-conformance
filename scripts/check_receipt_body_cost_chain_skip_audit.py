#!/usr/bin/env python3
"""Static guard for the receipt body cost/chain/skip audit memo."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIT = REPO_ROOT / "docs" / "internal" / "RECEIPT_BODY_COST_CHAIN_SKIP_AUDIT_v0_1_JUN07.md"

REQUIRED = (
    "tokens.fresh",
    "tokens.reused",
    "surprise_cause",
    "content_hash",
    "prev pointer",
    "skipped/no-op",
    "Cache keys are input identity only, never the decision.",
    "does not add new AdmissionDecision values",
    "srs_receipt_external_verifier.py",
)


def main() -> int:
    if not AUDIT.exists():
        print(f"FAIL: missing audit memo: {AUDIT.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1

    text = AUDIT.read_text(encoding="utf-8")
    failures: list[str] = []

    for needle in REQUIRED:
        if needle not in text:
            failures.append(f"missing required text: {needle}")

    # The required guardrail phrase contains these words in a negated sentence.
    # Reject only additional affirmative uses.
    without_required_guardrail = text.replace("does not add new AdmissionDecision values", "")
    if "add new AdmissionDecision" in without_required_guardrail:
        failures.append("contains affirmative AdmissionDecision expansion phrase")

    if "skipped AdmissionDecision" in text:
        failures.append("contains forbidden skipped AdmissionDecision phrase")

    if "\u2014" in text:
        failures.append("contains em dash character")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1

    print("PASS: receipt body cost/chain/skip audit static guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
