import pytest
from witness_market import WitnessServiceOffer,WitnessRequest,WitnessResult

def test_witness_market_preserves_non_equivalence():
    o=WitnessServiceOffer.build("node:w","receipt_witness","profile:srs-v1",("exact_bytes","observed_at"))
    r=WitnessRequest.build("sha256:"+"a"*64,o.offer_id,"receipt_witness")
    out=WitnessResult(r.request_id,"witness-observation:1","OBSERVED")
    assert o.authority_effect=="none" and o.truth_effect=="none"
    assert out.authority_effect=="none" and out.truth_effect=="none"

def test_truth_guarantee_refused():
    with pytest.raises(ValueError): WitnessServiceOffer.build("node:w","receipt_witness","p",("truth",))
