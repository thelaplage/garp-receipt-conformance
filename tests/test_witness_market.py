import pytest
from dataclasses import fields
from witness_market import WitnessServiceOffer,WitnessRequest,WitnessResult,reject_authority_injection

FORBIDDEN_FIELD_NAMES={"authority_effect","truth_effect"}

def test_witness_market_preserves_non_equivalence():
    o=WitnessServiceOffer.build("node:w","receipt_witness","profile:srs-v1",("exact_bytes","observed_at"))
    r=WitnessRequest.build("sha256:"+"a"*64,o.offer_id,"receipt_witness")
    out=WitnessResult(r.request_id,"witness-observation:1","OBSERVED")
    # No authority/truth-effect field is DEFINED on these objects at all --
    # non-authority is expressed by structural absence, not by a value.
    assert not FORBIDDEN_FIELD_NAMES.intersection(f.name for f in fields(o))
    assert not FORBIDDEN_FIELD_NAMES.intersection(f.name for f in fields(out))

def test_truth_guarantee_refused():
    with pytest.raises(ValueError): WitnessServiceOffer.build("node:w","receipt_witness","p",("truth",))

@pytest.mark.parametrize("payload",[
    {"authority_effect":"none"},
    {"authority_effect":"admitted"},
    {"trusted":True},
    {"admitted":True},
])
def test_authority_injection_rejected(payload):
    with pytest.raises(ValueError):
        reject_authority_injection(payload)
