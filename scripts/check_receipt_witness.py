#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.receipt_witness import ReceiptWitnessObservation, Signature, build_witness_set

DIGEST = "sha256:" + "a" * 64


def obs(node, ts, sig):
    return ReceiptWitnessObservation(
        receipt_digest=DIGEST,
        witness_node_id=node,
        observed_at=ts,
        signature=Signature(algorithm="ed25519", key_id=f"{node}:key", value=sig),
    )


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
    assert first["authority_effect"] == "none"

    bad = ReceiptWitnessObservation(
        receipt_digest=DIGEST,
        witness_node_id="node:bad",
        observed_at="2026-08-23T05:00:10Z",
        signature=Signature(algorithm="ed25519", key_id="k", value="s"),
        authority_effect="admit",
    )
    try:
        bad.validate()
    except ValueError:
        pass
    else:
        raise AssertionError("authority movement must be rejected")

    print("RECEIPT-WITNESS0 PASS")


if __name__ == "__main__":
    main()
