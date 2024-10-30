"""
See KB: https://support.datatrails.ai/hc/en-gb/articles/18120936244370-How-to-independently-verify-Merkle-Log-Events-recorded-on-the-DataTrails-transparency-ledger#h_01HTYDD6ZH0FV2K95D61RQ61ZJ
"""
from typing import List
import hashlib
import bencodepy

V3FIELDS = [
    "identity",
    "event_attributes",
    "asset_attributes",
    "operation",
    "behaviour",
    "timestamp_declared",
    "timestamp_accepted",
    "timestamp_committed",
    "principal_accepted",
    "principal_declared",
    "tenant_identity",
]


def leaf_hash(event: dict, domain=0) -> bytes:
    """
    Return the leaf hash which is proven by a scitt receipt for the provided CONFIRMED event

    Computes:

    SHA256(BYTE(0x00) || BYTES(idTimestamp) || BENCODE(redactedEvent))

    See KB: https://support.datatrails.ai/hc/en-gb/articles/18120936244370-How-to-independently-verify-Merkle-Log-Events-recorded-on-the-DataTrails-transparency-ledger#h_01HTYDD6ZH0FV2K95D61RQ61ZJ
    """
    salt = get_mmrsalt(event, domain)
    preimage = get_v3preimage(event)
    return hashlib.sha256(salt + preimage).digest()


def get_mmrsalt(event: dict, domain=0) -> List[bytes]:
    """
    Get the public salt details from a v3 event record.

    Returns the bytes comprised of

    DOMAIN || BYTES(IDTIMESTAMP)

    """

    # Note this value is also present in the trie index data in the public merkle log
    # which can be obtained directly from app.datatrails.ai/verifiabledata/merklelogs
    # without authentication. veracity provides cli tooling for this sort of thing.
    hexidtimestamp = event["merklelog_entry"]["commit"]["idtimestamp"]
    idtimestamp = bytes.fromhex(hexidtimestamp[2:])  # strip the epoch from the front
    return bytes([domain]) + idtimestamp


def get_v3preimage(event: dict) -> bytes:
    """
    Calculate the leaf hash of a V3 leaf
    """

    preimage = {}
    for field in V3FIELDS:
        # Ensure the leaf contains all required fields
        try:
            value = event[field]
        except KeyError:
            raise KeyError(f"V3 leaf is missing required field: {field}")

        preimage[field] = value

    # their is only one occurence
    if preimage["identity"].startswith("public"):
        preimage["identity"] = preimage["identity"].replace("public", "")

    return bencodepy.encode(preimage)
