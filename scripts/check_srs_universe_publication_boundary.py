#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "fixtures" / "srs-universe-publication-boundary-v0.1.json"
EXPECTED_IDS = {
    "valid_receipt_absent_counterpedia",
    "valid_receipt_no_local_artifact",
    "custody_without_publication",
    "publication_cannot_repair_malformed_receipt",
    "many_receipts_one_source",
    "many_replicas_one_artifact",
    "dagr_receipt_no_auto_publish",
    "current_countergraph_not_universal_srs_graph",
}


def derive(case):
    given = dict(case["input"])
    out = dict(given)

    if given.get("counterpedia_included") is False:
        out["receipt_nonexistent"] = False
    if given.get("local_artifact_present") is False and not given.get(
        "profile_requires_local_artifact", False
    ):
        out["locally_custodied"] = False
    if given.get("artifact_custodied") is True:
        out.setdefault("admitted", False)
    if given.get("receipt_valid") is False:
        # Publication/indexing is non-promoting: invalid stays invalid.
        out["receipt_valid"] = False
    if "source_identity_count" in given and "receipt_count" in given:
        out["source_identity_count"] = given["source_identity_count"]
        out["authority_increased_by_count"] = False
    if "artifact_identity_count" in given and "replica_count" in given:
        out["artifact_identity_count"] = given["artifact_identity_count"]
        out["importance_increased_by_replica_count"] = False
    if given.get("dagr_receipt_emitted") is True:
        out["auto_publish_counterpedia"] = False
    if given.get("current_countergraph_snapshot") is True:
        out["universal_srs_graph"] = False

    return out


def main():
    doc = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert doc["status"] == "implementation_guard"
    assert doc["canonical_doctrine_claim"] is False
    cases = doc["cases"]
    ids = {case["id"] for case in cases}
    assert ids == EXPECTED_IDS, (ids, EXPECTED_IDS)

    failures = []
    for case in cases:
        actual = derive(case)
        for key, expected in case["expected"].items():
            if actual.get(key) != expected:
                failures.append(
                    f"{case['id']}: {key} expected {expected!r}, got {actual.get(key)!r}"
                )

    if failures:
        raise SystemExit("\n".join(failures))

    print(
        "SRS-UNIVERSE-CONFORMANCE0: PASS "
        f"cases={len(cases)} canonical_doctrine_claim=false"
    )


if __name__ == "__main__":
    main()
