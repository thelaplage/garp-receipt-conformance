#!/usr/bin/env python3
"""Standalone verifier for ReceiptWitnessObservation records.

A ReceiptWitnessObservation is a signed claim of the form "witness node W
observed exact receipt bytes with digest D by time T". This verifier proves
BYTE-OBSERVATION VALIDITY ONLY:

    witnessed_bytes != valid_receipt != authorized_action != true_result
    != admitted_evidence

It does NOT prove that the witnessed receipt is a valid SRS envelope, that any
action the receipt describes was authorized, that any result the receipt
carries is true, or that the receipt (or anything it describes) has been
admitted anywhere. A witness observation is independent evidence of bytes
having been seen; nothing more. See ../README.md and
schemas/receipt-witness-observation.v0.1.json at the repo root.

It is intentionally dependency-light: Python 3 standard library only. It does
not import garp_sdk, arcs_amnesiac, garp_core, or any other Vega/GARP product
code, and it makes no network calls.

Usage (from the repository root):
    python3 packs/receipt-witness/v0.1/tools/verify_witness.py <observation.json> [...]
    python3 packs/receipt-witness/v0.1/tools/verify_witness.py --witness-set <observation.json> ...

Exit status: 0 if every given observation is a valid byte-observation (and,
with --witness-set, the set aggregates cleanly); 1 if any is invalid.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from tools.receipt_witness import (  # noqa: E402
    WitnessValidationError,
    build_witness_set,
    parse_observation,
    verify_observation,
)


def _load_json(path: Path) -> object:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def verify_file(path: Path) -> bool:
    """Verify one observation file; print a PASS/FAIL line (+ reason codes)."""
    try:
        data = _load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL  {path}  Could not read/parse witness observation.")
        print(f"        [UNREADABLE] {exc}")
        return False

    result = verify_observation(data)
    if result.byte_observation_valid:
        print(
            f"PASS  {path}  Valid witness observation: byte-observation only; "
            "asserts nothing about receipt validity, action authorization, "
            "factual truth, or admission."
        )
        return True

    print(f"FAIL  {path}  Invalid witness observation.")
    print(f"        [{result.code}] {result.reason}")
    return False


def print_witness_set(paths: list[Path]) -> bool:
    """Build and print the derived witness-set view for the given files.

    The witness-set view is a DERIVED aggregation only: it never replaces the
    primary observations (each remains independently addressable at its own
    path/digest) and witness_count is never a truth or admission signal.
    """
    observations = []
    for path in paths:
        try:
            data = _load_json(path)
            observations.append(parse_observation(data))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL  witness-set  Could not read/parse {path}.")
            print(f"        [UNREADABLE] {exc}")
            return False
        except WitnessValidationError as exc:
            print(f"FAIL  witness-set  {path} is not a valid witness observation.")
            print(f"        [{exc.code}] {exc.message}")
            return False

    try:
        derived = build_witness_set(observations)
    except WitnessValidationError as exc:
        print("FAIL  witness-set  Could not aggregate observations.")
        print(f"        [{exc.code}] {exc.message}")
        return False

    print(
        f"WITNESS-SET  receipt_digest={derived['receipt_digest']}  "
        f"witness_count={derived['witness_count']}"
    )
    for node in derived["witness_nodes"]:
        print(f"  witness_node: {node}")
    for digest in derived["observation_digests"]:
        print(f"  observation_digest: {digest}")
    print(
        "  note: witness_count is a count of independently addressable "
        "observations, not a verdict, admission, or truth signal."
    )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "observations",
        nargs="+",
        type=Path,
        help="witness observation JSON files",
    )
    parser.add_argument(
        "--witness-set",
        action="store_true",
        help="build and print the derived witness-set view for all given "
        "observations instead of verifying each independently",
    )
    args = parser.parse_args(argv)

    if args.witness_set:
        return 0 if print_witness_set(args.observations) else 1

    any_failed = False
    for path in args.observations:
        if not verify_file(path):
            any_failed = True
    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
