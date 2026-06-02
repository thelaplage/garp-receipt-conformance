#!/usr/bin/env python3
"""Parity + guard test for the portable standalone verifier.

This test proves two things the pack depends on:

1. NON-DIVERGENCE. The standalone verifier
   (``verify_standalone.py``) bundles a vendored copy of the envelope-validation
   logic so it can ship as a single portable artifact. This test runs BOTH the
   standalone verifier and the canonical in-repo validator
   (``tools/validate_srs_envelope.py``) over the pack's valid and invalid
   fixtures and asserts their envelope verdicts agree. If the vendored copy ever
   drifts from the canonical validator, this test fails — which is what lets the
   repo carry one portable artifact without authoring a *second divergent*
   verifier.

2. DETERMINISTIC, GUARDED OUTPUT. The standalone verifier's rendered reading and
   its full operator report match the committed expected assets byte-for-byte,
   the valid receipt verifies (exit 0), and the top-level status/verdict drift
   fixture fails (exit 1) at the envelope-invariant stage.

Standard library only. Run it directly:

    python3 packs/bedrock-openai-audit/v0.1/tools/test_verify_standalone.py
"""

from __future__ import annotations

import sys

# Load the verifier/validator by file path without leaving __pycache__ behind.
sys.dont_write_bytecode = True

import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PACK_ROOT = TOOLS_DIR.parent
REPO_ROOT = PACK_ROOT.parent.parent.parent

VALID = PACK_ROOT / "fixtures" / "valid" / "bedrock_openai_audit.envelope.json"
INVALID = PACK_ROOT / "fixtures" / "invalid" / "top_level_status_verdict.json"
INPUT = PACK_ROOT / "input" / "bedrock_openai_audit.input.json"
EXPECTED_READING = PACK_ROOT / "expected" / "valid" / "bedrock_openai_audit.reading.txt"
EXPECTED_REPORT = PACK_ROOT / "expected" / "valid" / "standalone_report.txt"
SCHEMA = REPO_ROOT / "schemas" / "srs-envelope" / "v0.1.0" / "srs-envelope.schema.json"
MANIFEST = (
    REPO_ROOT / "schemas" / "srs-envelope" / "v0.1.0" / "srs-envelope.schema.manifest.json"
)
CANONICAL_VALIDATOR = REPO_ROOT / "tools" / "validate_srs_envelope.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - import plumbing
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


vs = _load("verify_standalone", TOOLS_DIR / "verify_standalone.py")
canon = _load("validate_srs_envelope", CANONICAL_VALIDATOR)


_passed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global _passed
    if not condition:
        raise AssertionError(f"FAIL: {label}{(' — ' + detail) if detail else ''}")
    _passed += 1
    print(f"ok {_passed} - {label}")


def _canonical_codes(receipt_path: Path) -> list[str]:
    """Envelope error codes the canonical in-repo validator reports."""
    _manifest, schema, _digest = canon.load_canonical(MANIFEST, SCHEMA)
    return canon.validate_receipt(receipt_path, schema).codes


def _standalone_codes(receipt_path: Path) -> list[str]:
    """Envelope error codes the standalone verifier's vendored logic reports."""
    import json

    schema = json.loads(SCHEMA.read_bytes())
    receipt = json.loads(receipt_path.read_bytes())
    return vs.validate_envelope(receipt, schema).codes


def main() -> int:
    # --- 1. PARITY: valid fixture — both accept the envelope -----------------
    canon_valid = _canonical_codes(VALID)
    standalone_valid = _standalone_codes(VALID)
    check(
        "parity: canonical validator accepts the valid envelope",
        canon_valid == [],
        f"codes={canon_valid}",
    )
    check(
        "parity: standalone verifier accepts the valid envelope",
        standalone_valid == [],
        f"codes={standalone_valid}",
    )
    check(
        "parity: valid-envelope verdicts agree",
        canon_valid == standalone_valid,
        f"canonical={canon_valid} standalone={standalone_valid}",
    )

    # --- 2. PARITY: invalid drift fixture — both reject, same reason ---------
    canon_invalid = _canonical_codes(INVALID)
    standalone_invalid = _standalone_codes(INVALID)
    check(
        "parity: canonical validator rejects the drift fixture",
        "TOP_LEVEL_BODY_VERDICT" in canon_invalid,
        f"codes={canon_invalid}",
    )
    check(
        "parity: standalone verifier rejects the drift fixture",
        "TOP_LEVEL_BODY_VERDICT" in standalone_invalid,
        f"codes={standalone_invalid}",
    )
    check(
        "parity: drift-fixture verdicts agree",
        sorted(canon_invalid) == sorted(standalone_invalid),
        f"canonical={canon_invalid} standalone={standalone_invalid}",
    )

    # --- 3. GUARD: rendered reading matches the committed asset --------------
    import json

    receipt = json.loads(VALID.read_bytes())
    reading = vs.render_reading(receipt)
    check(
        "rendered reading matches expected/valid/bedrock_openai_audit.reading.txt",
        reading == EXPECTED_READING.read_text(encoding="utf-8"),
    )

    # --- 4. GUARD: full report matches the committed asset byte-for-byte -----
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc_valid = vs.main(
            [
                "--receipt", str(VALID),
                "--input", str(INPUT),
                "--schema", str(SCHEMA),
                "--manifest", str(MANIFEST),
                "--reading", str(EXPECTED_READING),
            ]
        )
    check(
        "valid receipt verifies (exit 0)",
        rc_valid == 0,
        f"exit={rc_valid}",
    )
    check(
        "full report matches expected/valid/standalone_report.txt byte-for-byte",
        buf.getvalue() == EXPECTED_REPORT.read_text(encoding="utf-8"),
    )

    # --- 5. GUARD: drift fixture fails (exit 1) -----------------------------
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc_invalid = vs.main(
            [
                "--receipt", str(INVALID),
                "--input", str(INPUT),
                "--schema", str(SCHEMA),
                "--manifest", str(MANIFEST),
                "--no-reading-check",
            ]
        )
    check(
        "drift fixture fails verification (exit 1)",
        rc_invalid == 1,
        f"exit={rc_invalid}",
    )
    check(
        "drift report records NOT VERIFIED",
        "Result: NOT VERIFIED" in buf.getvalue(),
    )

    print(f"PASS: standalone verifier parity + guard ({_passed} checks)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1)
