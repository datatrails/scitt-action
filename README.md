# scitt-action

GitHub Action for DataTrails implementation of [SCITT](https://scitt.io)

## Sample Code

This action prints "Hello World" or "Hello" + the name of a person to greet to the log.

## Inputs

## `scitt-client_id`

    **Required** The CLIENT_ID used to access the DataTrails SCITT APIs

## `scitt-secret`

    **Required** The SECRET used to access the DataTrails SCITT APIs

## `feed`

    **Required** Unique ID for the collection of statements about an artifact

## `payload`

    **Required** The payload file to be registered on the SCITT Service (eg: SBOM, Scan Result, Attestation)

## `content-type`

    **Required** The payload content type (iana mediaType) to be registered on the SCITT Service (eg: application/spdx+json, application/vnd.cyclonedx+json, Scan Result, Attestation)

## `signed-statement-file`

    **Optional** File representing the signed SCITT Statement that will be registered on SCITT.
    **default** 'signed-statement.cbor'

## `receipt-file`

    **Optional** The file to save the cbor receipt
    **default** 'receipt.cbor'

## `signing-key-file`

    **Required** The .pem file used to sign the statement

## `issuer`

    **Required** The name of the issuer, set to CTW_Claims:iss

## Example usage

```yaml
name: Docker Buil/Push, SCITT Register Synsation Web

on:
  push:
    branches: [ "main" ]

env:
  DATATRAILS_CLIENT_ID: ${{ secrets.DATATRAILS_CLIENT_ID }}
  DATATRAILS_SECRET: ${{ secrets.DATATRAILS_SECRET }}
  SYNSATION_SIGNING_KEY: ${{ secrets.SYNSATION_SIGNING_KEY }}
  FEED: `synsation.io/myproduct-v1.0`
jobs:
  build-image-register-DataTrails-SCITT:
    runs-on: ubuntu-latest
    # Sets the permissions granted to the `GITHUB_TOKEN` for the actions in this job.
    permissions:
      contents: read
      packages: write
      # 
    steps:
      - name: Create buildOutput Directory
        run: |
          mkdir -p ./buildOutput/
      - name: save-keys
        env:
          SIGNING_KEY: ${{ env.SYNSATION_SIGNING_KEY }}
        shell: bash
        run: |
          echo "$SIGNING_KEY" >> ./synsation.pem
      - name: Create Compliance Statement
        run: |
          echo '{"compliance.42":"true","software.eol":"2025-03-15"}' >> ./buildOutput/attestation.json
      - name: Register as a SCITT Signed Statement
        id: register-compliance-scitt-signed-statement
        uses: datatrails/scitt-action@v0.4
        with:
          scitt-client_id: ${{ env.DATATRAILS_CLIENT_ID }}
          scitt-secret: ${{ env.DATATRAILS_SECRET }}
          feed: ${{ env.FEED }}
          payload: "./buildOutput/attestation.json"
          content-type: "application/vnd.unknown.attestation+json"
          signing-key-file: "./synsation.pem"
          issuer: "synsation.io"
      - name: cleanup-keys
        shell: bash
        run: |
          rm ./synsation.pem
```
