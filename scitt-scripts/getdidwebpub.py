import re
import requests
from jwcrypto import jwk
from pycose.keys.curves import P384
from pycose.keys.keyparam import KpKty, EC2KpX, EC2KpY, KpKeyOps, EC2KpCurve
from pycose.keys.keytype import KtyEC2
from pycose.keys.keyops import VerifyOp
from pycose.keys import CoseKey
from pycose.headers import KID


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
