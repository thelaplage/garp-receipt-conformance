#!/usr/bin/env python3
from dataclasses import fields
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.receipt_witness import (
    ReceiptWitnessObservation,
    Signature,
    WitnessValidationError,
    build_witness_set,
    parse_observation,
)

DIGEST = "sha256:" + "a" * 64


def obs(node, ts, sig):
    return ReceiptWitnessObservation(
        receipt_digest=DIGEST,
        witness_node_id=node,
        observed_at=ts,
        signature=Signature(algorithm="ed25519", key_id=f"{node}:key", value=sig),
    )


def raw_dict(node="node:witness-x", ts="2026-08-23T05:00:10Z", sig="sig-x"):
    return {
        "schema": "receipt.witness_observation.v0_1",
        "receipt_digest": DIGEST,
        "witness_node_id": node,
        "observed_at": ts,
        "signature": {"algorithm": "ed25519", "key_id": f"{node}:key", "value": sig},
    }


def main():
    observations = [
        obs("node:witness-a", "2026-08-23T05:00:02Z", "sig-a"),
        obs("node:witness-b", "2026-08-23T05:00:05Z", "sig-b"),
        obs("node:witness-c", "2026-08-23T05:00:09Z", "sig-c"),
    ]
    first = build_witness_set(observations)
    second = build_witness_set(reversed(observations))
    assert first == second
    assert first["witness_count"] == 3
    assert "authority_effect" not in first, (
        "witness-set summary must not serialize authority_effect (structural absence)"
    )

    # No authority-shaped field is defined on the object at all: absence,
    # not a none-pinned value, is what expresses "no authority" here.
    field_names = {f.name for f in fields(ReceiptWitnessObservation)}
    for banned in ("authority_effect", "admission_effect", "trust_effect", "standing_effect"):
        assert banned not in field_names, (
            f"{banned} must be structurally absent from ReceiptWitnessObservation"
        )

    # Fail-closed: injecting an authority/trust/admission-shaped field into
    # untrusted input must be rejected outright, regardless of the value it
    # carries, because the field itself is not a recognized top-level field.
    hostile_injections = (
        ("authority_effect", "none"),
        ("authority_effect", "admitted"),
        ("trusted", True),
        ("admitted", True),
    )
    for key, value in hostile_injections:
        hostile = raw_dict()
        hostile[key] = value
        try:
            parse_observation(hostile)
        except WitnessValidationError as exc:
            assert exc.code == "ADDITIONAL_PROPERTIES", (
                f"expected fail-closed ADDITIONAL_PROPERTIES rejection of "
                f"injected {key}={value!r}, got {exc.code}"
            )
        else:
            raise AssertionError(f"injected {key}={value!r} must be rejected, was accepted")

    print("RECEIPT-WITNESS0 PASS")


if __name__ == "__main__":
    main()
