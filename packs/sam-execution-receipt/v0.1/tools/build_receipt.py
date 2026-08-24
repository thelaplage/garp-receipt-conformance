#!/usr/bin/env python3
"""SAM execution observation -> SRS envelope receipt adapter (SAM-EXECUTION-RECEIPT0).

SAM is the FIRST transport adapter this repo profiles for a *portable execution
receipt*: a receipt for one remote MCP tool invocation carried over a transport,
without treating transport authentication or successful execution as
evidentiary truth, admission, or publication.

This pack does NOT invent a new top-level receipt family. It EXTENDS the
existing canonical `sdk_enforcement` receipt_type (the closed-enum family this
repo already carries for SDK/transport-binding enforcement decisions over a
tool call) with a new GARP body_kind, `sam_execution_receipt`, carried under
`extensions.garp.body` exactly like every other pack in this repo. See
`docs/SAM_EXECUTION_RECEIPT_V0_1.md` for the full field/canonicalization spec
and `packs/sam-execution-receipt/v0.1/README.md` for what a receipt proves and
does not prove.

This is a *minimal*, deterministic, file-in/file-out adapter for one pack. It
is NOT an ESE / enforcement runtime, NOT a product, and NOT a live transport
integration: it reads one explicit, public-safe, SYNTHETIC SAM execution
observation file and emits one ARCS SRS *envelope* receipt. No SAM/DAGR-MCP
process is run, no network is touched, no credentials are read. (A repo-wide
search at authoring time found no live "SAM" transport implementation in this
repo or any sibling GARP/ARCS/DAGR repo; this pack follows the same
explicit-file-only discipline already established by
`packs/mcp-audit-trail/v0.1/` and `packs/bedrock-openai-audit/v0.1/` rather
than fabricating a pin to a system that does not exist on disk.)

What it does:
  * computes the sha256 of the exact input bytes and records it under
    ``extensions.garp.body.artifact_hashes`` (the receipt binds the input
    cryptographically),
  * maps ONLY the known SAM observation fields into a GARP body whose
    ``body_kind`` names the shape (``sam_execution_receipt``); any top-level
    input field the adapter does not recognize is listed by NAME ONLY under
    ``unrecognized_input_fields`` so it is visible without silently acquiring
    receipt meaning,
  * carries any policy decision and any parent/delegation lineage only as a
    REFERENCE (``decision_ref`` / ``delegation_ref``) and NEVER as a
    body-level or top-level ``verdict`` / ``status`` / ``disposition`` /
    ``decision`` / ``governance_state`` / ``admitted`` / ``verified`` /
    ``published``. This preserves Option A (decision_ref) as recorded in
    garp-ops PR #87 and garp-sdk PR #78, and extends the same discipline to
    delegation/lineage,
  * carries ``execution_outcome`` as a closed enum (``success``, ``refused``,
    ``transport_failure``, ``contaminated_response``) and NEVER fabricates a
    success payload digest for a non-success outcome: ``returned_payload_digest``
    is the literal string ``"unavailable"`` whenever no payload was actually
    produced or the produced bytes failed transport integrity checking.

What it does NOT do:
  * it does not assert that any recorded observation is true, that any
    invocation was authorized, that its output is true or evidence-supported,
    or that anything here is admitted or published. See
    ``ATTESTATION_LIMITS`` below and the core non-equivalences in
    ``docs/SAM_EXECUTION_RECEIPT_V0_1.md``.

Determinism: output is ``json.dumps(..., indent=2, sort_keys=True)`` plus a
trailing newline, with every timestamp/id derived only from the input
bytes/fields (no wall clock, no randomness), so regenerating from the same
input reproduces byte-identical output. Standard library only; imports no
garp_sdk, arcs_amnesiac, dagr_mcp, or other Vega/GARP/DAGR product code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

# receipt_type is the family axis. This pack EXTENDS the existing closed-enum
# `sdk_enforcement` family (SDK/transport-binding enforcement decisions over a
# tool call) rather than inventing a new top-level receipt family. See the
# "Integration seam" note in docs/dispatch/SAM-EXECUTION-RECEIPT0.md.
RECEIPT_TYPE = "sdk_enforcement"

# Pack-local, descriptive routing label. It is NOT a newly-minted canonical
# boundary_type: the canonical boundary_type lane remains arcs-srs's to define.
# `sdk_enforcement_boundary` was already seeded as the illustrative value for
# the `sdk_enforcement` receipt_type in fixtures/valid/sdk_enforcement.minimal.json;
# this pack is the first PACK to actually route on it. See
# docs/BOUNDARY_TYPE_LEDGER.md.
BOUNDARY_TYPE = "sdk_enforcement_boundary"

BODY_KIND = "sam_execution_receipt"
EXECUTION_RECEIPT_SCHEMA_VERSION = "sam-execution-receipt/v0.1"

VALID_EXECUTION_OUTCOMES = (
    "success",
    "refused",
    "transport_failure",
    "contaminated_response",
)

# Top-level SAM-observation input fields this adapter recognizes and maps.
# Anything else present in the input surfaces only as a bare field name under
# unrecognized_input_fields (see map_body below) -- it never silently acquires
# receipt semantics.
KNOWN_INPUT_FIELDS = {
    "sam_observation_schema",
    "invocation_id",
    "caller_ref",
    "service_ref",
    "mcp_tool_ref",
    "requested_at",
    "issued_at",
    "transport_session_ref",
    "transport_adapter",
    "decision_ref",
    "delegation_ref",
    "canonical_arguments_digest",
    "execution_outcome",
    "returned_payload_digest",
    "error_code",
    "error_observation_digest",
    "note",
}

ATTESTATION_LIMITS = [
    "this receipt attests SRS envelope shape, SAM-execution-receipt guardrails, "
    "and input-byte integrity only",
    "receipt_valid != action_authorized: a valid receipt does not establish that "
    "the invocation was authorized",
    "receipt_valid != output_true: a valid receipt does not establish that any "
    "returned content is true",
    "receipt_valid != output_evidence_supported: a valid receipt does not "
    "establish evidentiary standing for any returned content",
    "receipt_valid != admitted: a valid receipt does not itself admit the "
    "invocation; any policy decision is carried only as decision_ref",
    "receipt_valid != published: a valid receipt does not publish or make "
    "public any subject, artifact, or claim",
    "a contaminated_response outcome records that returned bytes failed "
    "transport integrity checking; no digest of the suspect bytes is carried "
    "as a trusted returned_payload_digest, and no claim is made about their "
    "content",
    "this is not a live transport integration: no SAM/DAGR-MCP process was "
    "run and no network was touched to build this receipt",
]

ARTIFACT_CLASSES_COVERED = ["trace", "packet_inspection"]
ARTIFACT_CLASSES_EXCLUDED = [
    "truth_verification",
    "action_authorization",
    "publication_eligibility",
    "evidentiary_support_determination",
]


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def map_body(observation: dict, input_label: str, input_digest: str) -> dict[str, Any]:
    outcome = observation.get("execution_outcome")
    if outcome not in VALID_EXECUTION_OUTCOMES:
        raise ValueError(
            f"execution_outcome {outcome!r} not in {VALID_EXECUTION_OUTCOMES}"
        )

    body: dict[str, Any] = {
        "body_kind": BODY_KIND,
        "execution_receipt_schema_version": EXECUTION_RECEIPT_SCHEMA_VERSION,
        "invocation_id": observation["invocation_id"],
        "caller_ref": observation["caller_ref"],
        "target_ref": observation["service_ref"],
        "mcp_tool_ref": observation["mcp_tool_ref"],
        "requested_at": observation["requested_at"],
        "transport_session_ref": observation["transport_session_ref"],
        "transport_adapter": {
            "adapter_id": observation["transport_adapter"]["adapter_id"],
            "source_revision": observation["transport_adapter"]["source_revision"],
        },
        "canonical_arguments_digest": observation["canonical_arguments_digest"],
        "execution_outcome": outcome,
        "returned_payload_digest": observation["returned_payload_digest"],
    }

    # Option A: any decision/delegation semantics are carried ONLY as a
    # reference, never as a verdict/grant. Both are optional ("when one
    # exists" / "when supplied").
    if observation.get("decision_ref") is not None:
        body["decision_ref"] = observation["decision_ref"]
    if observation.get("delegation_ref") is not None:
        body["delegation_ref"] = observation["delegation_ref"]

    # error_code / error_observation_digest are present only when applicable
    # (never fabricated for a success outcome; explicit null in the input
    # means "not observed", which we represent by omission).
    if observation.get("error_code") is not None:
        body["error_code"] = observation["error_code"]
    if observation.get("error_observation_digest") is not None:
        body["error_observation_digest"] = observation["error_observation_digest"]

    # Unknown/unsupported SAM fields do not silently acquire meaning: list the
    # NAMES only (never values) of any top-level input field this adapter does
    # not recognize.
    unrecognized = sorted(set(observation.keys()) - KNOWN_INPUT_FIELDS)
    if unrecognized:
        body["unrecognized_input_fields"] = unrecognized

    body["artifact_hashes"] = {input_label: f"sha256:{input_digest}"}
    return body


def build_receipt(input_path: Path) -> dict:
    raw = input_path.read_bytes()
    input_digest = sha256_of_bytes(raw)
    observation = json.loads(raw)

    input_label = f"input/{input_path.name}"
    body = map_body(observation, input_label, input_digest)

    receipt: dict[str, Any] = {
        "receipt_version": "srs.core.v5.1",
        "receipt_id": f"sam-execution-receipt-{body['execution_outcome']}-{input_digest[:16]}",
        "receipt_type": RECEIPT_TYPE,
        "boundary_type": BOUNDARY_TYPE,
        "protocol_binding": "garp",
        "subject_ref": observation["invocation_id"],
        "issued_at": observation["issued_at"],
        "retention_class_applied": "hash_only",
        "artifact_classes_covered": list(ARTIFACT_CLASSES_COVERED),
        "artifact_classes_excluded": list(ARTIFACT_CLASSES_EXCLUDED),
        "attestation_limits": list(ATTESTATION_LIMITS),
        "extensions": {"garp": {"body": body}},
    }
    return receipt


def render(receipt: dict) -> str:
    return json.dumps(receipt, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an SRS envelope receipt from a public-safe, synthetic "
        "SAM execution-observation input file (envelope form + SAM-execution-"
        "receipt guardrails + input-byte integrity only; not a live transport "
        "integration).",
    )
    parser.add_argument("input", type=Path, help="SAM execution-observation input JSON")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the receipt here; default is stdout",
    )
    args = parser.parse_args(argv)

    try:
        receipt = build_receipt(args.input)
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
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
