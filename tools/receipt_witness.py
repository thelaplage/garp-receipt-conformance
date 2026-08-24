"""Receipt witness observation helpers.

A witness attests only that it observed exact receipt bytes by a stated time.
It does not attest receipt validity, action authorization, factual truth, or
admission. See schemas/receipt-witness-observation.v0.1.json for the wire
schema this module implements.

Required invariant (RECEIPT-WITNESS0):
    witnessed_bytes != valid_receipt != authorized_action != true_result
    != admitted_evidence

No authority/admission/trust-shaped field (e.g. `authority_effect`) is
defined anywhere on this object. "No authority" is expressed by that
field's structural absence, not by serializing it pinned to a benign value:
the schema is closed (`additionalProperties: false`) and this module's
`REQUIRED_TOP_LEVEL_FIELDS` is the only field set `parse_observation`
accepts, so an untrusted payload that tries to add such a field (whatever
value it carries) is rejected outright, before any other check runs.

No blockchain, no consensus protocol, no global timestamp authority, and no
truth-from-count: `build_witness_set` below only ever aggregates independently
addressable observations. A higher witness_count is not, and must never be
read as, stronger evidence of truth, authorization, or admission.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, field
from typing import Iterable

SCHEMA_ID = "receipt.witness_observation.v0_1"

REQUIRED_TOP_LEVEL_FIELDS = (
    "schema",
    "receipt_digest",
    "witness_node_id",
    "observed_at",
    "signature",
)
REQUIRED_SIGNATURE_FIELDS = ("algorithm", "key_id", "value")


class WitnessValidationError(ValueError):
    """A witness observation failed validation.

    Subclasses ValueError so existing `except ValueError` call sites keep
    working; `code` gives a stable, machine-checkable reason token so
    conformance vectors can assert *why* a fixture was rejected, not just
    that it was.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


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

    def validate(self) -> None:
        if self.schema != SCHEMA_ID:
            raise WitnessValidationError(
                "SCHEMA_MISMATCH", f"unsupported witness schema {self.schema!r}"
            )
        if not self.receipt_digest.startswith("sha256:") or len(self.receipt_digest) != 71:
            raise WitnessValidationError(
                "DIGEST_FORMAT",
                f"invalid receipt digest {self.receipt_digest!r} "
                "(expected 'sha256:' + 64 lowercase hex chars)",
            )
        try:
            int(self.receipt_digest[7:], 16)
        except ValueError as exc:
            raise WitnessValidationError(
                "DIGEST_FORMAT", f"receipt digest is not valid hex: {exc}"
            ) from exc
        if len(self.witness_node_id) < 3:
            raise WitnessValidationError(
                "NODE_ID_TOO_SHORT",
                f"invalid witness node id {self.witness_node_id!r} (minLength 3)",
            )
        if not self.observed_at.endswith("Z"):
            raise WitnessValidationError(
                "OBSERVED_AT_FORMAT",
                f"observed_at {self.observed_at!r} must be UTC RFC3339 ('Z' suffix)",
            )
        if not all((self.signature.algorithm, self.signature.key_id, self.signature.value)):
            raise WitnessValidationError(
                "SIGNATURE_INCOMPLETE", "signature envelope is incomplete"
            )

    def canonical_bytes(self) -> bytes:
        payload = asdict(self)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def observation_digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()


@dataclass(frozen=True)
class ObservationVerification:
    """Result of verifying one witness observation.

    `byte_observation_valid` is the *only* claim this result makes. The
    `asserts_*` fields are fixed at False and are carried on the result
    itself (not just in a docstring) so a caller cannot mistake byte-
    observation validity for a stronger claim without reading past the
    dataclass shape.
    """

    byte_observation_valid: bool
    code: str | None = None
    reason: str | None = None
    asserts_receipt_validity: bool = field(default=False, init=False)
    asserts_action_authorization: bool = field(default=False, init=False)
    asserts_factual_truth: bool = field(default=False, init=False)
    asserts_admission: bool = field(default=False, init=False)


def parse_observation(data: dict) -> ReceiptWitnessObservation:
    """Parse + validate a raw dict against the witness-observation shape.

    Enforces the schema's `additionalProperties: false` / `required` shape
    (schemas/receipt-witness-observation.v0.1.json) before handing off to
    `ReceiptWitnessObservation.validate()` for the domain-level invariants.
    """
    if not isinstance(data, dict):
        raise WitnessValidationError("NOT_OBJECT", "witness observation must be a JSON object")

    extra = sorted(set(data) - set(REQUIRED_TOP_LEVEL_FIELDS))
    if extra:
        raise WitnessValidationError(
            "ADDITIONAL_PROPERTIES", f"unexpected top-level field(s): {extra}"
        )
    missing = [f for f in REQUIRED_TOP_LEVEL_FIELDS if f not in data]
    if missing:
        raise WitnessValidationError(
            "MISSING_FIELD", f"missing required top-level field(s): {missing}"
        )

    sig_data = data["signature"]
    if not isinstance(sig_data, dict):
        raise WitnessValidationError("SIGNATURE_SHAPE", "signature must be a JSON object")
    sig_extra = sorted(set(sig_data) - set(REQUIRED_SIGNATURE_FIELDS))
    if sig_extra:
        raise WitnessValidationError(
            "ADDITIONAL_PROPERTIES", f"unexpected signature field(s): {sig_extra}"
        )
    sig_missing = [f for f in REQUIRED_SIGNATURE_FIELDS if f not in sig_data]
    if sig_missing:
        raise WitnessValidationError(
            "MISSING_FIELD", f"missing required signature field(s): {sig_missing}"
        )
    for key in REQUIRED_SIGNATURE_FIELDS:
        if not isinstance(sig_data[key], str):
            raise WitnessValidationError(
                "SIGNATURE_SHAPE", f"signature.{key} must be a string"
            )

    for key in ("schema", "receipt_digest", "witness_node_id", "observed_at"):
        if not isinstance(data[key], str):
            raise WitnessValidationError("SCHEMA_MISMATCH", f"{key} must be a string")

    observation = ReceiptWitnessObservation(
        receipt_digest=data["receipt_digest"],
        witness_node_id=data["witness_node_id"],
        observed_at=data["observed_at"],
        signature=Signature(**sig_data),
        schema=data["schema"],
    )
    observation.validate()
    return observation


def verify_observation(data: dict) -> ObservationVerification:
    """Verify byte-observation validity only.

    This is the required verification API: it returns whether `data` is a
    well-formed, internally-consistent witness observation, and nothing else.
    It does not, and cannot, upgrade the underlying receipt to valid, the
    underlying action to authorized, the underlying result to true, or the
    underlying evidence to admitted.
    """
    try:
        parse_observation(data)
    except WitnessValidationError as exc:
        return ObservationVerification(byte_observation_valid=False, code=exc.code, reason=exc.message)
    return ObservationVerification(byte_observation_valid=True)


def build_witness_set(observations: Iterable[ReceiptWitnessObservation]) -> dict:
    rows = list(observations)
    for observation in rows:
        observation.validate()
    receipt_digests = {row.receipt_digest for row in rows}
    if len(receipt_digests) != 1:
        raise WitnessValidationError(
            "MULTIPLE_RECEIPT_DIGESTS", "a witness set must refer to one receipt digest"
        )
    # Derived summary only; primary observations remain independently addressable.
    # witness_count is a count of observations, never a verdict, admission, or
    # truth signal (truth-from-count is an explicit non-goal of this schema).
    # No authority/admission-shaped field is added to this summary either —
    # the same structural-absence invariant applies to derived views as to
    # the primary observations.
    return {
        "receipt_digest": next(iter(receipt_digests)),
        "witness_count": len(rows),
        "witness_nodes": sorted({row.witness_node_id for row in rows}),
        "observation_digests": sorted(row.observation_digest() for row in rows),
    }
