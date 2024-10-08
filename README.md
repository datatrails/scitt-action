# GitHub Action for the DataTrails SCITT Implementation

Secure your Software Supply Chain and your Content Authenticity with immutable data trails. This GitHub Action uses DataTrails implementation of the IETF Supply Chain, Integrity and Trust ([SCITT](https://scitt.io)) APIs.

**NOTE:**:  
This SCITT GitHub Action is in Preview, pending adoption of the [SCITT Reference APIs (SCRAPI)](https://datatracker.ietf.org/doc/draft-ietf-scitt-scrapi/).
To use a production supported implementation, please contact [DataTrails](https://www.datatrails.ai/contactus/) for more info.

## Getting Started

To create immutable data trails, an account with a `Client_ID` and `Secret` are required.
To get started, [Sign Up here](https://app.datatrails.ai/signup), then see [Creating Access Tokens Using a Custom Integration](https://docs.datatrails.ai/developers/developer-patterns/getting-access-tokens-using-app-registrations/).

## Inputs

## `datatrails-client_id`

**Required** The `CLIENT_ID` used to access the DataTrails SCITT APIs

## `datatrails-secret`

**Required** The `SECRET` used to access the DataTrails SCITT APIs

## `subject`

**Required** Unique ID for the collection of statements about an artifact. For more info, see `subject` in the [IETF SCITT Terminology](https://datatracker.ietf.org/doc/html/draft-ietf-scitt-architecture#name-terminology).

## `payload`

**Required** The payload file to be registered on the SCITT Service (eg: SBOM, Scan Result, Attestation)

## `content-type`

**Required** The payload content type (iana mediaType) to be registered on the SCITT Service (eg: `application/spdx+json`, `application/vnd.cyclonedx+json`, Scan Result, Attestation, ...)

## `signed-statement-file`

**Optional** A required file representing the signed SCITT Statement that will be registered on SCITT. The parameter is optional, as it provides a default file name.  
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

## Example Usage

The following example shows a minimal implementation for registering SCITT Signed Statements.

Three GitHub Action Secrets are used:

- `secrets.DATATRAILS_CLIENT_ID`
- `secrets.DATATRAILS_CLIENT_SECRET`
- `secrets.SIGNING_KEY`

### Registering Signed Statements

Sample github `action.yaml`

```yaml
name: Register SCITT Statement

on:
  workflow_dispatch:
  # push:
    # branches: [ "main" ]

env:
  DATATRAILS_CLIENT_ID: ${{ secrets.DATATRAILS_CLIENT_ID }}
  DATATRAILS_CLIENT_SECRET: ${{ secrets.DATATRAILS_CLIENT_SECRET }}
  SIGNING_KEY: ${{ secrets.SYNSATION_SIGNING_KEY }}
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
      - name: Upload Attestation
        id: upload-attestation
        uses: actions/upload-artifact@v4
        with:
          name: attestation.json
          path: ./buildOutput/attestation.json
      - name: Register as a SCITT Signed Statement
        # Register the Signed Statement wit DataTrails SCITT APIs
        id: register-compliance-scitt-signed-statement
        uses: datatrails/scitt-action@v0.6.1
        with:
          content-type: "application/vnd.unknown.attestation+json"
          payload-file: "./buildOutput/attestation.json"
          payload-location: ${{ steps.upload-attestation.outputs.artifact-url }}
          subject: ${{ env.SUBJECT }}
          issuer: ${{ env.ISSUER}}
          signing-key-file: "./signingkey.pem"
      - name: upload-transparent-statement
        uses: actions/upload-artifact@v4
        with:
          name: transparent-statement
          path: transparent-statement.cbor
      - name: cleanup-keys
        shell: bash
        run: |
          rm ./signingkey.pem
```

### Querying DataTrails Events

Registered SCITT Statements are available as [DataTrails Events][datatrails-events].

> **NOTE**: As the [SCITT Reference API][scrapi] queries mature, additional DataTrails SCITT Query APIs will be made available.

Using the `SUBJECT` from above, query all DataTrails Events (SCITT Registered Statements).

```bash
SUBJECT="synsation.io/myproduct-v1.0"
curl https://app.datatrails.ai/archivist/v2/publicassets/-/events?event_attributes.subject=$SUBJECT \
  | jq
```

## Next Steps

- [Getting started with SCITT & DataTrails][datatrails-scitt-preview]
- [DigiCert Software Trust Manager - SCITT GitHub Action][digicert-scitt-action]
- [IETF SCITT Working Group][ietf-scitt-wg]
- [SCITT Community][scitt-community]
- [SCITT Slack][scitt-slack]

[datatrails-events]:        https://docs.datatrails.ai/developers/api-reference/events-api/
[datatrails-scitt-preview]: https://docs.datatrails.ai/developers/developer-patterns/scitt-api/
[digicert-scitt-action]:    https://github.com/digicert/scitt-action/
[ietf-scitt-wg]:            https://datatracker.ietf.org/wg/scitt/about/
[scitt-community]:          https://scitt.io
[scitt-slack]:              https://ietf.slack.com/archives/C03PXCAR206
[scrapi]:                   https://datatracker.ietf.org/doc/draft-ietf-scitt-scrapi/
