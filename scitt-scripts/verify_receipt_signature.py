""" Module for verifying the counter signed receipt signature """

import re
from base64 import b64decode
import argparse

import requests

from jwcrypto import jwk

from pycose.messages import Sign1Message
from pycose.keys.curves import P384
from pycose.keys.keyparam import KpKty, EC2KpX, EC2KpY, KpKeyOps, EC2KpCurve
from pycose.keys.keytype import KtyEC2
from pycose.keys.keyops import VerifyOp
from pycose.keys import CoseKey
from pycose.headers import KID

HEADER_LABEL_DID = 391


def open_receipt(receipt_file: str) -> str:
    """
    opens the receipt from the receipt file.
    NOTE: the receipt is expected to be in base64 encoding.
    """
    with open(receipt_file, encoding="UTF-8") as file:
        receipt = file.read()
        return receipt


def get_didweb_pubkey(didurl: str, kid: bytes) -> dict:
    """
    gets the given did web public key, given the key ID (kid) and didurl.
    see https://w3c-ccg.github.io/did-method-web/
    NOTE: expects the key to be ecdsa P-384.
    """

    # check the didurl is a valid did web url
    # pylint: disable=line-too-long
    pattern = r"did:web:(?P<host>[a-zA-Z0-9/.\-_]+)(?:%3A(?P<port>[0-9]+))?(:*)(?P<path>[a-zA-Z0-9/.:\-_]*)"
    match = re.match(pattern, didurl)

    if not match:
        raise ValueError("DID is not a valid did:web")

    # convert the didweb url into a url:
    #
    #  e.g. did:web:example.com:foo:bar
    #  becomes: https://example.com/foo/bar/did.json
    groups = match.groupdict()
    host = groups["host"]
    port = groups.get("port")  # might be None
    path = groups["path"]

    origin = f"{host}:{port}" if port else host

    protocol = "https"

    decoded_partial_path = path.replace(":", "/")

    endpoint = (
        f"{protocol}://{origin}/{decoded_partial_path}/did.json"
        if path
        else f"{protocol}://{origin}/.well-known/did.json"
    )

    # do a https GET on the url to get the did document
    resp = requests.get(endpoint, timeout=60)
    assert resp.status_code == 200

    did_document = resp.json()

    # now search the verification methods for the correct public key
    for verification_method in did_document["verificationMethod"]:
        if verification_method["publicKeyJwk"]["kid"] != kid.decode("utf-8"):
            continue

        x_part = verification_method["publicKeyJwk"]["x"]
        y_part = verification_method["publicKeyJwk"]["y"]

        cose_key = {
            KpKty: KtyEC2,
            EC2KpCurve: P384,
            KpKeyOps: [VerifyOp],
            EC2KpX: jwk.base64url_decode(x_part),
            EC2KpY: jwk.base64url_decode(y_part),
        }

        return cose_key

    raise ValueError(f"no key with kid: {kid} in verification methods of did document")


def verify_receipt(receipt: str) -> bool:
    """
    verifies the counter signed receipt signature
    """

    # base64 decode the receipt into a cose sign1 message
    b64decoded_message = b64decode(receipt)

    # decode the cbor encoded cose sign1 message
    message = Sign1Message.decode(b64decoded_message)

    # get the verification key from didweb
    kid: bytes = message.phdr[KID]
    didurl = message.phdr[HEADER_LABEL_DID]

    cose_key_dict = get_didweb_pubkey(didurl, kid)
    cose_key = CoseKey.from_dict(cose_key_dict)

    message.key = cose_key

    # verify the counter signed receipt signature
    verified = message.verify_signature()

    return verified


def main():
    """Verifies a counter signed receipt signature"""

    parser = argparse.ArgumentParser(description="Create a signed statement.")

    # signing key file
    parser.add_argument(
        "--receipt-file",
        type=str,
        help="filepath to the stored receipt, in base64 format.",
        default="scitt-receipt.txt",
    )

    args = parser.parse_args()

    receipt = open_receipt(args.receipt_file)

    verified = verify_receipt(receipt)

    print(verified)


if __name__ == "__main__":
    main()
