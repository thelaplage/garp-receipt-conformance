"""Receipt witness observation helpers.

A witness attests only that it observed exact receipt bytes by a stated time.
It does not attest receipt validity, action authorization, factual truth, or
admission.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class Signature:
    algorithm: str
    key_id: str
    value: str


@dataclass(frozen=True)
class ReceiptWitnessObservation:
    receipt_digest: str
    witness_node_id: str
    observed_at: str
    signature: Signature
    schema: str = "receipt.witness_observation.v0_1"
    authority_effect: str = "none"

    def validate(self) -> None:
        if self.schema != "receipt.witness_observation.v0_1":
            raise ValueError("unsupported witness schema")
        if self.authority_effect != "none":
            raise ValueError("witness observation cannot move authority")
        if not self.receipt_digest.startswith("sha256:") or len(self.receipt_digest) != 71:
            raise ValueError("invalid receipt digest")
        int(self.receipt_digest[7:], 16)
        if len(self.witness_node_id) < 3:
            raise ValueError("invalid witness node id")
        if not self.observed_at.endswith("Z"):
            raise ValueError("observed_at must be UTC RFC3339")
        if not all((self.signature.algorithm, self.signature.key_id, self.signature.value)):
            raise ValueError("signature envelope is incomplete")

    def canonical_bytes(self) -> bytes:
        payload = asdict(self)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def observation_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()


def build_witness_set(observations: Iterable[ReceiptWitnessObservation]) -> dict:
    rows = list(observations)
    for observation in rows:
        observation.validate()
    receipt_digests = {row.receipt_digest for row in rows}
    if len(receipt_digests) != 1:
        raise ValueError("a witness set must refer to one receipt digest")
    # Derived summary only; primary observations remain independently addressable.
    return {
        "receipt_digest": next(iter(receipt_digests)),
        "witness_count": len(rows),
        "witness_nodes": sorted({row.witness_node_id for row in rows}),
        "observation_digests": sorted(row.observation_digest() for row in rows),
        "authority_effect": "none",
    }
