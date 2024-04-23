# GitHub Action for creating and registering SCITT statements with Software Trust Manager and DataTrails

This GitHub Action provides the ability to create and sign [SCITT](https://datatracker.ietf.org/wg/scitt/about/) statements using code signing keys protected by DigiCert [Software Trust Manager](https://www.digicert.com/software-trust-manager) and submit these statements to the transparency service operated by [DataTrails](https://www.datatrails.ai/).

## Getting Started

1. Generate a keypair and corresponding end-entity certificate in [Software Trust Manager](https://www.digicert.com/software-trust-manager)
2. [Create an account](https://app.datatrails.ai/signup) at DataTrails and [create an access token](https://docs.datatrails.ai/developers/developer-patterns/getting-access-tokens-using-app-registrations/)

## Action Inputs

## `datatrails-client_id`

**Required** The `CLIENT_ID` used to access the DataTrails SCITT APIs

## `datatrails-secret`

**Required** The `SECRET` used to access the DataTrails SCITT APIs

## `subject`

**Required** Unique ID for the collection of statements about an artifact. For more info, see `subject` in the [IETF SCITT Terminology](https://datatracker.ietf.org/doc/html/draft-ietf-scitt-architecture#name-terminology).

### `payload`

**Required** The payload file to be registered on the SCITT Service (SBOM, Scan Result, Attestation, etc.)

### `content-type`

**Required** The payload content type (IANA media type) to be registered on the SCITT Service. For example: `application/spdx+json`

### `signed-statement-file`

**Optional** A required file representing the signed SCITT Statement that will be registered with the SCITT Transparency Service. The parameter is optional, as it provides a default file name.  
See [Signed Statement Issuance and Registration](https://datatracker.ietf.org/doc/html/draft-ietf-scitt-architecture#name-signed-statement-issuance-a)
**Default** 'signed-statement.cbor'

## `receipt-file`

**Optional** The file name used to return a cbor receipt (NOT CURRENTLY IMPLEMENTED)
**Default** 'receipt.cbor'

## `signing-key-file`

**Required** The `.pem` file used to sign the statement. NOTE: This version requires a local private key. The key may be volume mapped, with future versions supporting remote signing services.

## `issuer`

**Required** The name of the issuer, set to `CTW_Claims:iss`.  
See [Signed Statement Envelope](https://datatracker.ietf.org/doc/html/draft-ietf-scitt-architecture#name-signed-statement-envelope).

## Example usage

The following example shows a minimal implementation.

Three GitHub Action Secrets are used:

- `secrets.DATATRAILS_CLIENT_ID`
- `secrets.DATATRAILS_SECRET`
- `secrets.SIGNING_KEY`

Sample github `action.yaml`

```yaml
name: Register SCITT Statement

on:
  push:
    branches: [ "main" ]

env:
  DATATRAILS_CLIENT_ID: ${{ secrets.DATATRAILS_CLIENT_ID }}
  DATATRAILS_SECRET: ${{ secrets.DATATRAILS_SECRET }}
  SIGNING_KEY: ${{ secrets.SIGNING_KEY }}
  SUBJECT: "synsation.io/myproduct-v1.0"
  ISSUER: "synsation.io"
jobs:
  build-image-register-DataTrails-SCITT:
    runs-on: ubuntu-latest
    # Sets the permissions granted to the `GITHUB_TOKEN` for the actions in this job.
    permissions:
      contents: read
      packages: write
    steps:
      - name: Create buildOutput Directory
        run: |
          mkdir -p ./buildOutput/
      - name: save-keys
        env:
          SIGNING_KEY: ${{ env.SIGNING_KEY }}
        shell: bash
        run: |
          echo "$SIGNING_KEY" >> ./signingkey.pem
      - name: Create Compliance Statement
        # A sample compliance file. Replace with an SBOM, in-toto statement, image for content authenticity, ...
        run: |
          echo '{"compliance.42":"true","software.eol":"2025-03-15"}' >> ./buildOutput/attestation.json
      - name: Register as a SCITT Signed Statement
        # Register the Signed Statement wit DataTrails SCITT APIs
        id: register-compliance-scitt-signed-statement
        uses: datatrails/scitt-action@v0.4
        with:
          datatrails-client_id: ${{ env.DATATRAILS_CLIENT_ID }}
          datatrails-secret: ${{ env.DATATRAILS_SECRET }}
          subject: ${{ env.SUBJECT }}
          payload: "./buildOutput/attestation.json"
          content-type: "application/vnd.unknown.attestation+json"
          signing-key-file: "./signingkey.pem"
          issuer: ${{ env.ISSUER}}
      - name: cleanup-keys
        shell: bash
        run: |
          rm ./signingkey.pem
```

## Secrets

This action requires secrets containing credentials and keypair information be configured. Specifically, the following secrets are required:

### DIGICERT_STM_CERTIFICATE_ID

ID of the certificate and keypair protected in Software Trust Manager

### DIGICERT_STM_API_KEY

The Software Trust Manager API key

### DIGICERT_STM_API_BASE_URI

The base URI of the Software Trust manager API

### DIGICERT_STM_API_CLIENTAUTH_P12_B64

The base-64 encoded PKCS #12 file for client authentication to the Software Trust Manager API

### DIGICERT_STM_API_CLIENTAUTH_P12_PASSWORD

The password for the PKCS #12 file for client authentication to the Software Trust Manager API

