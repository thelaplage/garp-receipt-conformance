#!/usr/bin/env python3
"""Witness-market scenario -> SRS envelope receipt adapter.

This is a *minimal*, deterministic, file-in/file-out adapter for one pack. It is
NOT an ESE / enforcement runtime and it is NOT a product. It reads one
public-safe witness-market scenario input file and emits one ARCS SRS
*envelope* receipt that carries the market-transaction record (a
WitnessServiceOffer, a WitnessRequest, and a WitnessResult) as a GARP body
under ``extensions.garp.body``.

What a witness-market transaction is (and is not)
--------------------------------------------------

A market participant offers a receipt-observation/verification/storage/replay
service (``WitnessServiceOffer``); a requester binds that offer to the exact
digest of a receipt it wants observed (``WitnessRequest``); the provider
returns a reference to a native witness/verification artifact
(``WitnessResult``). None of the three carries truth or authority effect:

    witness_offer_exists != witness_selected != receipt_observed
        != receipt_valid != action_authorized != result_true

Witness count never substitutes for verification or admission. This adapter
does not assert that the subject receipt is valid, that any action described
by it was authorized, or that the observation is true — it attests envelope
shape and input-byte integrity only, exactly like every other pack in this
repository.

Determinism: output is ``json.dumps(..., indent=2, sort_keys=True)`` plus a
trailing newline, with ``issued_at`` and ``receipt_id`` derived only from the
input bytes/fields (no wall clock, no randomness), so regenerating from the
same input reproduces byte-identical output. Standard library only.

The market contract dataclasses (``WitnessServiceOffer``, ``WitnessRequest``,
``WitnessResult``) live in ``witness_market.py`` at the repository root; this
adapter loads that module by file path so it works regardless of the caller's
working directory or ``sys.path`` state.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

PACK_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACK_ROOT.parent.parent.parent
WITNESS_MARKET_MODULE = REPO_ROOT / "witness_market.py"

# Pack-local, descriptive routing label. It is NOT a newly-minted canonical
# boundary_type: the canonical boundary_type lane remains arcs-srs's to define.
# It names how this receipt routes (a witness-market transaction record) and
# nothing more. See README.md ("boundary_type").
BOUNDARY_TYPE = "witness_market_boundary"

# receipt_type is the family axis; "provenance" is the closed-enum family this
# evidence shape belongs to (a witness-market transaction is provenance over a
# receipt-observation request, not sdk_enforcement/grace_session/connection).
RECEIPT_TYPE = "provenance"

ATTESTATION_LIMITS = [
    "this receipt attests SRS envelope shape and input-byte integrity only",
    "it does not assert that the subject receipt (subject_ref) is valid",
    "it does not assert that any action described by the subject receipt was authorized",
    "it does not assert that the witness observation/result is true",
    "witness_offer_exists != witness_selected != receipt_observed != receipt_valid "
    "!= action_authorized != result_true",
    "witness count never substitutes for verification or admission",
]


def _load_witness_market():
    spec = importlib.util.spec_from_file_location(
        "witness_market", WITNESS_MARKET_MODULE
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load witness_market from {WITNESS_MARKET_MODULE}")
    module = importlib.util.module_from_spec(spec)
    # Register under its real name before exec: the dataclass machinery
    # (frozen=True, slots=True) looks the module up via sys.modules while
    # processing class bodies, which fails if it is not registered yet.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_receipt(input_path: Path) -> dict:
    wm = _load_witness_market()

    raw = input_path.read_bytes()
    input_digest = sha256_of_bytes(raw)
    scenario = json.loads(raw)

    offer = wm.WitnessServiceOffer.build(
        provider_node_id=scenario["provider_node_id"],
        service_kind=scenario["service_kind"],
        profile_ref=scenario["profile_ref"],
        guarantees=tuple(scenario.get("guarantees", ())),
    )
    request = wm.WitnessRequest.build(
        receipt_digest=scenario["subject_receipt_digest"],
        service_offer_id=offer.offer_id,
        requested_service=scenario["requested_service"],
    )
    result = wm.WitnessResult(
        request_id=request.request_id,
        native_artifact_ref=scenario["native_artifact_ref"],
        status=scenario["result_status"],
    )

    body: dict[str, Any] = {
        "body_kind": "witness_market_transaction",
        "offer": {
            "provider_node_id": offer.provider_node_id,
            "service_kind": offer.service_kind,
            "profile_ref": offer.profile_ref,
            "guarantees": list(offer.guarantees),
            "offer_id": offer.offer_id,
            "authority_effect": offer.authority_effect,
            "truth_effect": offer.truth_effect,
        },
        "request": {
            "receipt_digest": request.receipt_digest,
            "service_offer_id": request.service_offer_id,
            "requested_service": request.requested_service,
            "request_id": request.request_id,
        },
        "result": {
            "request_id": result.request_id,
            "native_artifact_ref": result.native_artifact_ref,
            "status": result.status,
            "authority_effect": result.authority_effect,
            "truth_effect": result.truth_effect,
        },
        "invariant_chain": [
            "witness_offer_exists",
            "witness_selected",
            "receipt_observed",
            "receipt_valid",
            "action_authorized",
            "result_true",
        ],
        "artifact_hashes": {
            "input/witness_market.input.json": f"sha256:{input_digest}",
        },
    }

    receipt: dict[str, Any] = {
        "receipt_version": "srs.core.v5.1",
        "receipt_id": f"witness-market-{input_digest[:16]}",
        "receipt_type": RECEIPT_TYPE,
        "boundary_type": BOUNDARY_TYPE,
        "protocol_binding": "garp",
        "subject_ref": scenario["subject_receipt_digest"],
        "issued_at": scenario["issued_at"],
        "artifact_classes_covered": [
            "trace",
            "provenance",
        ],
        "artifact_classes_excluded": [
            "truth_verification",
            "authorization_grant",
            "admission_decision",
        ],
        "attestation_limits": list(ATTESTATION_LIMITS),
        "extensions": {"garp": {"body": body}},
    }
    return receipt


def render(receipt: dict) -> str:
    return json.dumps(receipt, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an SRS envelope receipt from a public-safe "
        "witness-market scenario input file (envelope form + input-byte "
        "integrity only; no truth or authority effect).",
    )
    parser.add_argument("input", type=Path, help="witness-market scenario input JSON")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the receipt here; default is stdout",
    )
    args = parser.parse_args(argv)

    try:
        receipt = build_receipt(args.input)
    except (OSError, json.JSONDecodeError, KeyError, ValueError, ImportError) as exc:
        print(f"FATAL: could not build receipt: {exc}", file=sys.stderr)
        return 2

    output = render(receipt)
    if args.out is None:
        sys.stdout.write(output)
    else:
        args.out.write_text(output, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
