""" Module for verifying the counter signed receipt signature """
from typing import List, Dict
from dataclasses import dataclass

import re
from base64 import b64decode
import argparse

import cbor2

from pycose.keys.curves import P384
from pycose.keys.keytype import KtyEC2
from pycose.keys.keyparam import KpKty, KpKeyOps, KpAlg, EC2KpD, EC2KpX, EC2KpY, EC2KpCurve
from pycose.keys.keyops import VerifyOp
from pycose.keys import CoseKey
from pycose.headers import KID, Algorithm
from pycose.messages.cosebase import CoseBase
from pycose.messages import Sign1Message
from pycose.messages.signcommon import SignCommon

from mmriver_algorithms import included_root

# COSE Receipts headers
# https://cose-wg.github.io/draft-ietf-cose-merkle-tree-proofs/draft-ietf-cose-merkle-tree-proofs.html#name-new-entries-to-the-cose-hea
HEADER_LABEL_DID = 391
HEADER_LABEL_COSE_RECEIPTS_VDS = 395
HEADER_LABEL_COSE_RECEIPTS_VDP = 396
HEADER_LABEL_COSE_RECEIPTS_INCLUSION_PROOFS = -1
# MMRIVER headers
# https://robinbryce.github.io/draft-bryce-cose-merkle-mountain-range-proofs/draft-bryce-cose-merkle-mountain-range-proofs.html#name-receipt-of-inclusion
HEADER_LABEL_MMRIVER_VDS_TREE_ALG = 2
HEADER_LABEL_MMRIVER_INCLUSION_PROOF_INDEX = 1
HEADER_LABEL_MMRIVER_INCLUSION_PROOF_PATH = 2

# CWT header label comes from version 4 of the scitt architecture document
# https://www.ietf.org/archive/id/draft-ietf-scitt-architecture-04.html#name-issuer-identity
HEADER_LABEL_CWT = 13

# Various CWT header labels come from:
# https://www.rfc-editor.org/rfc/rfc8392.html#section-3.1
HEADER_LABEL_CWT_ISSUER = 1
HEADER_LABEL_CWT_SUBJECT = 2

# CWT CNF header labels come from:
# https://datatracker.ietf.org/doc/html/rfc8747#name-confirmation-claim
HEADER_LABEL_CWT_CNF = 8
HEADER_LABEL_CNF_COSE_KEY = 1

# CWT CNF header labels come from:
# https://datatracker.ietf.org/doc/html/rfc8747#name-confirmation-claim
HEADER_LABEL_CWT_CNF = 8
HEADER_LABEL_CNF_COSE_KEY = 1


def cnf_key_from_phdr(phdr: dict) -> CoseKey:
    """
    Extracts the confirmation key from the cwt claims.
    """
    cwt_claims = phdr.get(HEADER_LABEL_CWT)
    # Note: issuer is the key vault key identity, subject is the tenant's merkle log tile path
    cnf_claim = cwt_claims.get(HEADER_LABEL_CWT_CNF)
    if not cnf_claim:
        raise ValueError("Missing confirmation claim in cwt claims")
    key = cnf_claim.get(HEADER_LABEL_CNF_COSE_KEY)
    if not key:
        raise ValueError("Missing confirmation key in cwt claims")
    
    key = key.copy()

    # There is a legacy "deliberate" bug in the common datatrails cose library, due to a short cut for jwt compatibility.
    # We encode the key as 'EC', the cose spec sais it MUST be 'EC2'
    if key.get(KpKty.identifier) == "EC":
        key[KpKty.identifier] = KtyEC2.identifier

    # A bug in our implementation sets key curve as 'P-384' rather than 'P_384'.
    if key[EC2KpCurve.identifier] == "P-384":
        key[EC2KpCurve.identifier] = P384.identifier

    if not KpKeyOps.identifier in key:
        key[KpKeyOps.identifier] = [VerifyOp]

    try:
        key = CoseKey.from_dict(key)
    except Exception as e:
        raise ValueError(f"Error extracting confirmation key: {e}")
    return key


def verify_receipt(receipt: bytes, leaf: bytes) -> bool:
    """
    Verifies the counter signed receipt signature
    Args:
        receipt: COSE Receipt as cbor encoded bytes
        leaf: append only log leaf hash proven by the receipt. provided as bytes
    """

    message = decode_sign1_detached(receipt)

    # While many proofs may be supplied, only the first is used here.
    # The checks will raise unless there is at least one proof found.
    # Note that when the proof is None it means the inclusion path is empty and the leaf is the payload of the receipt.
    # (And is also a direct member of the accumulator)
    proof = mmriver_inclusion_proofs(message.phdr, message.uhdr)[0]
    path = proof.path or []

    root = included_root(proof.index, leaf, path)
    message.payload = root

    # Extract the signing key from the cwt claims in the protected header
    # The receipt signing key is the merklelog consistency checkpoint siging key.
    # Which is declared publicly in many places including the DataTrails web ui.
    # Note that this is *not* the same as the signed statement counter signing key.

    signing_key = cnf_key_from_phdr(message.phdr)
    message.key = signing_key
    return message.verify_signature()


@dataclass
class InclusionProof:
    index: int
    path: List[bytes]


def mmriver_inclusion_proofs(phdr: dict, uhdr: dict) -> List[InclusionProof]:
    """
    Checks the headers of the mmriver receipt for the correct values
    and returns a list of inclusion proofs.
    """
    # check the receipt headers
    try:
        vds = phdr[HEADER_LABEL_COSE_RECEIPTS_VDS]
    except KeyError:
        raise KeyError("Missing COSE Receipt VDS header")

    if vds != HEADER_LABEL_MMRIVER_VDS_TREE_ALG:
        raise ValueError("COSE Receipt VDS tree algorithm is not MMRIVER")

    try:
        vds = uhdr[HEADER_LABEL_COSE_RECEIPTS_VDP]
    except KeyError:
        raise KeyError("Missing COSE Receipt VDS header")

    try:
        inclusion_proofs = vds[HEADER_LABEL_COSE_RECEIPTS_INCLUSION_PROOFS]
    except KeyError:
        raise KeyError("Missing COSE Receipt VDS inclusion proof")

    if len(inclusion_proofs) == 0:
        raise ValueError("COSE Receipt VDS inclusion proof count is not at least 1")

    proofs: List[Dict] = []
    # Now check the MMRIVER specifics
    for inclusion_proof in inclusion_proofs:
        if HEADER_LABEL_MMRIVER_INCLUSION_PROOF_INDEX not in inclusion_proof:
            raise ValueError("Missing mmr-index from MMRIVER COSE Receipt of inclusion")
        if HEADER_LABEL_MMRIVER_INCLUSION_PROOF_PATH not in inclusion_proof:
            raise ValueError(
                "Missing inclusion-proof from MMRIVER COSE Receipt of inclusion"
            )

        proofs.append(
            InclusionProof(
                inclusion_proof[HEADER_LABEL_MMRIVER_INCLUSION_PROOF_INDEX],
                inclusion_proof[HEADER_LABEL_MMRIVER_INCLUSION_PROOF_PATH],
            )
        )

    return proofs


def decode_sign1_detached(
    message: bytes, payload=None, *args, **kwargs
) -> Sign1Message:
    """
    Decodes a COSE sign1 message from a message with a detached payload.

    For COSE Receipts the caller can not provide payload in advance.
    The payload is dependent on the receipt's unprotected header contents which are only available
    after calling this function.

    WARNING: The message will NOT VERIFY unless the payload is replaced with the payload that was signed.

    Args:
        message: the bytes of the COSE sign1 message
        payload:
            Used as the payload if not none, otherwise payload is forced to b''.
            Verification will fail until the correct payload has been set on the returned
            Sign1Message.
        args: passed on to Sign1Message.__init__
        kwargs: passed on to Sign1Message.__init__
    """
    # decode the cbor encoded cose sign1 message, per the CoseBase implementation
    try:
        cbor_msg = cbor2.loads(message)
        cose_obj = cbor_msg.value
    except AttributeError:
        raise AttributeError("Message was not tagged.")
    except ValueError:
        raise ValueError("Decode accepts only bytes as input.")

    if payload is None:
        payload = b""

    cose_obj[2] = payload # force replace with b'' if payload is detached, due to lack of pycose support
    return Sign1Message.from_cose_obj(cose_obj, True)


def is_hexadecimal(s: str) -> bool:
    """
    Checks if a string is hexadecimal. The string may optionally start with '0x'.
    The exact string '0x' is also considered valid.
    """
    pattern = r"^0x[0-9a-fA-F]*$|^[0-9a-fA-F]+$"
    return bool(re.match(pattern, s))


def open_receipt(receipt_file: str) -> str:
    """
    opens the receipt from the receipt file.
    NOTE: the receipt is expected to be in base64 encoding.
    """
    with open(receipt_file, encoding="UTF-8") as file:
        receipt = file.read()
        return receipt


def main():
    """Verifies a signed statement receipt

    The inclusion proof is verified to produce the receipt payload.
    The receipt signature is then verified.

    The leaf value is the merkle log entry committing the statement to the append only log.
    For the DataTrails platform, the leaf hash is available in the ui.
    It can also be produced from the event data returned by the events api.
    The event data includes the signed statement, allong with other platform specific metadata,
    that can be ignored by generic scitt consumers.
    """

    parser = argparse.ArgumentParser(
        description="Verify the receipt for a signed statement."
    )

    # signing key file
    parser.add_argument(
        "--receipt-file",
        type=str,
        help="filepath to the stored receipt, in base64 format.",
        default="scitt-receipt.txt",
    )
    parser.add_argument(
        "--leaf", type=str, help="The append only log leaf hash proven by the receipt."
    )

    args = parser.parse_args()

    receipt_b64 = open_receipt(args.receipt_file)
    receipt = b64decode(receipt_b64)
    verified = verify_receipt(receipt, bytes.fromhex(args.leaf))

    print(verified)


if __name__ == "__main__":
    main()
