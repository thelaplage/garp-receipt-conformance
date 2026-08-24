#!/usr/bin/env python3
"""Witness-market invariant guard.

Exercises ``witness_market.py`` (repository root) directly and asserts the
properties this pack depends on:

1. The valid fixture's offer and result both carry authority_effect="none"
   and truth_effect="none" (a witness never gains authority).
2. The chain of market-transaction identifiers does not collapse: offer_id,
   request_id, the subject receipt_digest, and the native_artifact_ref are
   four distinct strings, and the request/result correctly bind back to the
   offer/request they reference (no silent identifier substitution).
3. The six-state invariant declared by the receipt body
   (``witness_offer_exists != witness_selected != receipt_observed !=
   receipt_valid != action_authorized != result_true``) is carried verbatim
   and its six tokens are pairwise distinct.
4. ``WitnessServiceOffer.build`` refuses every forbidden truth/authority
   guarantee (``truth``, ``authorized``, ``admitted``, ``trusted``).
5. ``WitnessServiceOffer.build`` refuses an unsupported service_kind.
6. ``WitnessRequest.build`` refuses a receipt_digest that is not
   ``sha256:``-prefixed and refuses an unsupported requested_service.
7. ``WitnessResult`` refuses a status outside {PASS, FAIL, NOT_EVALUATED,
   OBSERVED} and refuses an empty native_artifact_ref.

Standard library only. Run directly from the repository root:

    python3 packs/witness-market/v0.1/tools/check_invariant_guard.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = PACK_ROOT.parent.parent.parent
WITNESS_MARKET_MODULE = REPO_ROOT / "witness_market.py"
VALID_FIXTURE = PACK_ROOT / "fixtures" / "valid" / "witness_market.envelope.json"

EXPECTED_INVARIANT_CHAIN = [
    "witness_offer_exists",
    "witness_selected",
    "receipt_observed",
    "receipt_valid",
    "action_authorized",
    "result_true",
]

FORBIDDEN_GUARANTEES = ("truth", "authorized", "admitted", "trusted")


def _load_witness_market():
    spec = importlib.util.spec_from_file_location(
        "witness_market", WITNESS_MARKET_MODULE
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load witness_market from {WITNESS_MARKET_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def check_valid_fixture_no_authority_or_truth_effect(body: dict) -> None:
    offer, result = body["offer"], body["result"]
    assert offer["authority_effect"] == "none", "offer.authority_effect must be 'none'"
    assert offer["truth_effect"] == "none", "offer.truth_effect must be 'none'"
    assert result["authority_effect"] == "none", "result.authority_effect must be 'none'"
    assert result["truth_effect"] == "none", "result.truth_effect must be 'none'"


def check_identifier_non_collapse(body: dict) -> None:
    offer, request, result = body["offer"], body["request"], body["result"]
    ids = {
        "offer_id": offer["offer_id"],
        "request_id": request["request_id"],
        "receipt_digest": request["receipt_digest"],
        "native_artifact_ref": result["native_artifact_ref"],
    }
    assert len(set(ids.values())) == len(ids), f"identifiers collapsed: {ids}"
    # Binding correctness: request/result reference the offer/request they
    # were built from, not some other transaction.
    assert request["service_offer_id"] == offer["offer_id"], (
        "request.service_offer_id must bind to offer.offer_id"
    )
    assert result["request_id"] == request["request_id"], (
        "result.request_id must bind to request.request_id"
    )


def check_invariant_chain_declared_and_distinct(body: dict) -> None:
    chain = body["invariant_chain"]
    assert chain == EXPECTED_INVARIANT_CHAIN, f"invariant_chain drifted: {chain}"
    assert len(set(chain)) == len(chain), f"invariant_chain states collapsed: {chain}"


def check_forbidden_guarantees_refused(wm) -> None:
    for guarantee in FORBIDDEN_GUARANTEES:
        try:
            wm.WitnessServiceOffer.build(
                "node:w", "receipt_witness", "profile:p", (guarantee,)
            )
        except ValueError:
            continue
        raise AssertionError(f"forbidden guarantee {guarantee!r} was not refused")


def check_unsupported_service_kind_refused(wm) -> None:
    try:
        wm.WitnessServiceOffer.build("node:w", "receipt_delete", "profile:p", ())
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported service_kind 'receipt_delete' was not refused")


def check_malformed_witness_request_refused(wm) -> None:
    try:
        wm.WitnessRequest.build("not-a-sha256-digest", "offer:1", "receipt_witness")
    except ValueError:
        pass
    else:
        raise AssertionError("non-sha256-prefixed receipt_digest was not refused")

    try:
        wm.WitnessRequest.build("sha256:" + "a" * 64, "offer:1", "receipt_delete")
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported requested_service was not refused")


def check_malformed_witness_result_refused(wm) -> None:
    try:
        wm.WitnessResult("request:1", "native:1", "AUTHORIZED")
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported result status was not refused")

    try:
        wm.WitnessResult("request:1", "", "OBSERVED")
    except ValueError:
        pass
    else:
        raise AssertionError("empty native_artifact_ref was not refused")


CHECKS = [
    ("no authority/truth effect on valid fixture's offer and result", check_valid_fixture_no_authority_or_truth_effect),
    ("market identifiers do not collapse and bind correctly", check_identifier_non_collapse),
    ("invariant chain declared verbatim with distinct states", check_invariant_chain_declared_and_distinct),
]

MODULE_CHECKS = [
    ("forbidden truth/authority guarantees refused", check_forbidden_guarantees_refused),
    ("unsupported service_kind refused", check_unsupported_service_kind_refused),
    ("malformed witness request refused", check_malformed_witness_request_refused),
    ("malformed witness result refused", check_malformed_witness_result_refused),
]


def main() -> int:
    body = json.loads(VALID_FIXTURE.read_text())["extensions"]["garp"]["body"]
    wm = _load_witness_market()

    failures: list[str] = []
    for name, fn in CHECKS:
        try:
            fn(body)
        except AssertionError as exc:
            failures.append(f"{name}: {exc}")
        else:
            print(f"ok - {name}")

    for name, fn in MODULE_CHECKS:
        try:
            fn(wm)
        except AssertionError as exc:
            failures.append(f"{name}: {exc}")
        else:
            print(f"ok - {name}")

    if failures:
        print("FAIL witness-market invariant guard:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"PASS witness-market invariant guard ({len(CHECKS) + len(MODULE_CHECKS)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
