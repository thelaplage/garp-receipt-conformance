from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from typing import Mapping,Any

SERVICES=frozenset({"receipt_verify","receipt_witness","receipt_store","replay_verify"})

def _digest(v:Mapping[str,Any])->str:
    return "sha256:"+hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

@dataclass(frozen=True,slots=True)
class WitnessServiceOffer:
    provider_node_id:str
    service_kind:str
    profile_ref:str
    guarantees:tuple[str,...]
    offer_id:str
    authority_effect:str="none"
    truth_effect:str="none"

    @classmethod
    def build(cls,provider_node_id:str,service_kind:str,profile_ref:str,guarantees=()):
        if service_kind not in SERVICES: raise ValueError("unsupported witness service")
        if not provider_node_id or not profile_ref: raise ValueError("provider/profile required")
        gs=tuple(sorted(set(guarantees)))
        forbidden={"truth","authorized","admitted","trusted"}
        if forbidden.intersection(gs): raise ValueError("witness offer may not promise truth/authority")
        body={"provider_node_id":provider_node_id,"service_kind":service_kind,"profile_ref":profile_ref,"guarantees":gs,"authority_effect":"none","truth_effect":"none"}
        oid="witness-service-offer:"+_digest(body).split(":",1)[1]
        return cls(provider_node_id,service_kind,profile_ref,gs,oid)

@dataclass(frozen=True,slots=True)
class WitnessRequest:
    receipt_digest:str
    service_offer_id:str
    requested_service:str
    request_id:str

    @classmethod
    def build(cls,receipt_digest,service_offer_id,requested_service):
        if not receipt_digest.startswith("sha256:") or requested_service not in SERVICES: raise ValueError("invalid request")
        body={"receipt_digest":receipt_digest,"service_offer_id":service_offer_id,"requested_service":requested_service}
        return cls(receipt_digest,service_offer_id,requested_service,"witness-request:"+_digest(body).split(":",1)[1])

@dataclass(frozen=True,slots=True)
class WitnessResult:
    request_id:str
    native_artifact_ref:str
    status:str
    authority_effect:str="none"
    truth_effect:str="none"

    def __post_init__(self):
        if self.status not in {"PASS","FAIL","NOT_EVALUATED","OBSERVED"}: raise ValueError("invalid status")
        if not self.native_artifact_ref: raise ValueError("native artifact ref required")
