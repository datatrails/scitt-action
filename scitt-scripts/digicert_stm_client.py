import base64
import os
import requests_pkcs12
from cryptography import x509
from cryptography.hazmat.primitives import hashes

from identity import Identity
from key import IssuerPrivateKey


class DigiCertSoftwareTrustManagerClient:
    def __init__(self):
        self._certificate_id = os.environ['DIGICERT_STM_CERTIFICATE_ID']
        self._stm_api_key = os.environ['DIGICERT_STM_API_KEY']
        self._stm_api_base_uri = os.environ['DIGICERT_STM_API_BASE_URI']
        self._stm_api_clientauth_p12 = base64.b64decode(os.environ['DIGICERT_STM_API_CLIENTAUTH_P12_B64'])
        self._stm_api_clientauth_p12_password = os.environ['DIGICERT_STM_API_CLIENTAUTH_P12_PASSWORD']

    def _execute_request(self, method, uri, body_json=None):
        uri = f'{self._stm_api_base_uri.rstrip("/")}/{uri.lstrip("/")}'

        headers = {
            'X-API-Key': self._stm_api_key,
        }

        if body_json:
            headers['Content-Type'] = 'application/json'

        resp = method(
            uri,
            pkcs12_data=self._stm_api_clientauth_p12,
            pkcs12_password=self._stm_api_clientauth_p12_password,
            headers=headers,
            json=body_json
        )

        resp.raise_for_status()

        return resp

    def _execute_get_request(self, uri, body_json=None):
        return self._execute_request(requests_pkcs12.get, uri, body_json)

    def _execute_post_request(self, uri, body_json=None):
        return self._execute_request(requests_pkcs12.post, uri, body_json)

    def retrieve_identity(self) -> Identity:
        resp = self._execute_get_request(f'/api/v1/certificates/{self._certificate_id}')

        j = resp.json()

        ee_cert = x509.load_der_x509_certificate(base64.b64decode(j['cert']))

        ica_info = next(c for c in j['chain'] if c['cert_type'] == 'intermediate')
        ica_cert = x509.load_der_x509_certificate(base64.b64decode(ica_info['blob']))

        kid = j['keypair']['id']

        return Identity(ee_cert, ica_cert, kid)

    @classmethod
    def _convert_der_ecdsa_sig_to_cose(cls, signature_octets):
        assert signature_octets[0] == 0x30
        assert signature_octets[1] < 0x80

        offset = 2

        b = bytearray()

        # loop to extract r and s
        for _ in range(2):
            assert signature_octets[offset] == 0x02  # INTEGER
            offset += 1

            value_len = signature_octets[offset]
            offset += 1

            value = signature_octets[offset:offset + value_len]

            # strip leading 0 octet (to force a positive)
            if value_len > 32 and value[0] == 0x00:
                value = value[1:]

            b.extend(value)

            offset += value_len

        return b

    def sign(self, issuer: Identity, message: bytes) -> bytes:
        # HACK: allow other algorithms
        h = hashes.Hash(hashes.SHA256())
        h.update(message)
        digest = h.finalize()

        body = {
            # HACK: allow other algorithms
            'sig_alg': 'sha256WithECDSA',

            'hash': base64.b64encode(digest).decode()
        }

        resp = self._execute_post_request(f'/api/v1/keypairs/{issuer.kid}/sign', body_json=body)

        j = resp.json()

        sig_der = base64.b64decode(j['signature'])

        return self._convert_der_ecdsa_sig_to_cose(sig_der)


class DigiCertStmPrivateKey(IssuerPrivateKey):
    def __init__(self):
        self._backend_instance = DigiCertSoftwareTrustManagerClient()

    def sign(self, message: bytes) -> bytes:
        return self._backend_instance.sign(self._backend_instance.retrieve_identity(), message)
