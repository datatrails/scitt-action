from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pycose.algorithms import Sha256


class Identity:
    def __init__(self, identity_document: x509.Certificate, ica_certificate: x509.Certificate, kid: str):
        self._identity_document = identity_document
        self._ica_certificate = ica_certificate
        self._kid = kid

        ekus = self._identity_document.extensions.get_extension_for_oid(x509.OID_EXTENDED_KEY_USAGE)

        assert x509.OID_CODE_SIGNING in ekus.value

        assert isinstance(self._identity_document.public_key(), ec.EllipticCurvePublicKey)
        assert isinstance(self._identity_document.public_key().curve, ec.SECP256R1)

    @property
    def identity_document_fingerprint(self):
        return self._identity_document.fingerprint(hashes.SHA256())

    @property
    def x5t(self):
        return [Sha256, self.identity_document_fingerprint]

    @property
    def iss(self):
        return self.identity_document_fingerprint.hex()

    @property
    def public_key(self):
        return self._identity_document.public_key()

    @property
    def kid(self):
        return self._kid

    @property
    def x5chain(self):
        return [
            c.public_bytes(serialization.Encoding.DER)
            for c in (self._identity_document, self._ica_certificate)
        ]
