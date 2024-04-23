""" Module for creating a SCITT signed statement """

import argparse
import hashlib
import json

from ecdsa import SigningKey
from pycose.algorithms import Es256
from pycose.headers import Algorithm, KID, ContentType, X5t, X5chain
from pycose.keys.curves import P256
from pycose.keys.keyparam import KpKty, EC2KpX, EC2KpY, EC2KpCurve
from pycose.keys.keytype import KtyEC2
from pycose.messages import Sign1Message

import digicert_stm_client
import identity
import key

# subject header label comes from version 2 of the scitt architecture document
# https://www.ietf.org/archive/id/draft-birkholz-scitt-architecture-02.html#name-envelope-and-claim-format
HEADER_LABEL_FEED = 392

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


def open_signing_key(key_file: str) -> SigningKey:
    """
    opens the signing key from the key file.
    NOTE: the signing key is expected to be a P-256 ecdsa key in PEM format.
    """
    with open(key_file, encoding="UTF-8") as file:
        signing_key = SigningKey.from_pem(file.read(), hashlib.sha256)
        return signing_key


def open_payload(payload_file: str) -> str:
    """
    opens the payload from the payload file.
    NOTE: the payload is expected to be in json format.
          however, any payload of type bytes is allowed.
    """
    with open(payload_file, encoding="UTF-8") as file:
        payload = json.loads(file.read())

        # convert the payload to a cose sign1 payload
        payload = json.dumps(payload, ensure_ascii=False)

        return payload


def create_signed_statement(
    issuer: identity.Identity,
    payload: str,
    subject: str,
    private_key: key.IssuerPrivateKey,
    content_type: str,
) -> bytes:
    """
    creates a signed statement, given the private key, payload, subject and issuer
    """

    ec_public_numbers = issuer.public_key.public_numbers()

    x_part = ec_public_numbers.x.to_bytes(32, byteorder='big')
    y_part = ec_public_numbers.y.to_bytes(32, byteorder='big')

    # create a protected header where
    #  the verification key is attached to the cwt claims
    protected_header = {
        Algorithm: Es256,
        KID: issuer.kid.encode(),
        ContentType: content_type,
        HEADER_LABEL_FEED: subject,
        X5t: issuer.x5t,
        HEADER_LABEL_CWT: {
            HEADER_LABEL_CWT_ISSUER: issuer.iss,
            HEADER_LABEL_CWT_SUBJECT: subject,
            HEADER_LABEL_CWT_CNF: {
                HEADER_LABEL_CNF_COSE_KEY: {
                    KpKty: KtyEC2,
                    EC2KpCurve: P256,
                    EC2KpX: x_part,
                    EC2KpY: y_part,
                },
            },
        },
    }

    unprotected_header = {
        X5chain: issuer.x5chain
    }

    # create the statement as a sign1 message using the protected header,
    # unprotected header, and payload
    statement = Sign1Message(
        phdr=protected_header,
        uhdr=unprotected_header,
        payload=payload.encode("utf-8")
    )

    # HACK: get TBS
    tbs = statement._sig_structure

    # HACK: this is gross
    statement._signature = private_key.sign(tbs)

    # encode the statement again to include the signature foisted into the object
    encoded = statement.encode(sign=False)

    return encoded


def main():
    """Creates a signed statement"""

    parser = argparse.ArgumentParser(description="Create a signed statement.")

    # payload-file (a reference to the file that will become the payload of the SCITT Statement)
    parser.add_argument(
        "--payload-file",
        type=str,
        help="filepath to the content that will become the payload of the SCITT Statement "
        "(currently limited to json format).",
        default="scitt-payload.json",
    )

    # content-type
    parser.add_argument(
        "--content-type",
        type=str,
        help="The iana.org media type for the payload",
        default="application/json",
    )

    # subject
    parser.add_argument(
        "--subject",
        type=str,
        required=True,
        help="subject to correlate statements made about an artifact.",
    )

    # output file
    parser.add_argument(
        "--output-file",
        type=str,
        help="name of the output file to store the signed statement.",
        default="signed-statement.cbor",
    )

    args = parser.parse_args()

    payload = open_payload(args.payload_file)

    stm_client = digicert_stm_client.DigiCertSoftwareTrustManagerClient()

    signed_statement = create_signed_statement(
        stm_client.retrieve_identity(),
        payload,
        args.subject,
        digicert_stm_client.DigiCertStmPrivateKey(),
        args.content_type
    )

    with open(args.output_file, "wb") as output_file:
        output_file.write(signed_statement)


if __name__ == "__main__":
    main()
