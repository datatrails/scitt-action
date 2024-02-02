import base64

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec


class Identity:
    _KNOWN_OID_TO_NAME_MAPPINGS = {
        x509.NameOID.COMMON_NAME: 'CN',
        x509.NameOID.LOCALITY_NAME: 'L',
        x509.NameOID.STATE_OR_PROVINCE_NAME: 'ST',
        x509.NameOID.ORGANIZATION_NAME: 'O',
        x509.NameOID.ORGANIZATIONAL_UNIT_NAME: 'OU',
        x509.NameOID.COUNTRY_NAME: 'C',
        x509.NameOID.STREET_ADDRESS: 'STREET',
    }

    def __init__(self, identity_document: x509.Certificate, ca_document: x509.Certificate, kid: str):
        self._identity_document = identity_document
        self._ca_document = ca_document
        self._kid = kid

        attribute_pairs = self._get_subject_attribute_type_value_pairs()

        # mismatch in lengths means there are duplicate attributes
        assert len(attribute_pairs) == len(set((a for a, _ in attribute_pairs)))

        ekus = self._identity_document.extensions.get_extension_for_oid(x509.OID_EXTENDED_KEY_USAGE)

        assert x509.OID_CODE_SIGNING in ekus.value

        assert isinstance(self._identity_document.public_key(), ec.EllipticCurvePublicKey)
        assert isinstance(self._identity_document.public_key().curve, ec.SECP256R1)

    def _get_subject_attribute_type_value_pairs(self):
        return [
            (self._KNOWN_OID_TO_NAME_MAPPINGS.get(na.oid, na.oid.dotted_string), na.value)
            for na in self._identity_document.subject
        ]

    @property
    def iss(self):
        # HACK: hardcoded fingerprint hash algorithm
        issuer_fingerprint = base64.urlsafe_b64encode(self._ca_document.fingerprint(hashes.SHA256())).decode()

        attribute_pairs = self._get_subject_attribute_type_value_pairs()

        subject = ':'.join((f'{a}:{v}' for a, v in attribute_pairs))

        return f'did:x509:0:sha256:{issuer_fingerprint}::subject:{subject}::eku:{x509.OID_CODE_SIGNING.dotted_string}'

    @property
    def public_key(self):
        return self._identity_document.public_key()

    @property
    def kid(self):
        return self._kid
