#!/bin/bash -l

set -e

# Uncomment for debugging
# echo "content-type:              " ${1}
# echo "datatrails-client_id:      " ${2}
# echo "datatrails-secret:         " ${3}
# echo "issuer:                    " ${4}
# echo "payload-file:              " ${5}
# echo "payload-location:          " ${6}
# echo "transparent-satement-file: " ${7}
# echo "signing-key-file:          " ${8}
# echo "skip-receipt:              " ${9}
# echo "subject:                   " ${10}

CONTENT_TYPE=${1}
DATATRAILS_CLIENT_ID=${2}
DATATRAILS_SECRET_ID=${3}
ISSUER=${4}
PAYLOAD_FILE=${5}
PAYLOAD_LOCATION=${6}
TRANSPARENT_STATEMENT_FILE=${7}
SIGNING_KEY_FILE=${8}
SKIP_RECEIPT=${9}
SUBJECT=${10}

SIGNED_STATEMENT_FILE="signed-statement.cbor"
TOKEN_FILE="./bearer-token.txt"

echo "Create an access token"
/scripts/create-token.sh ${DATATRAILS_CLIENT_ID} ${DATATRAILS_SECRET_ID} $TOKEN_FILE

# ls -a

# ls -la $TOKEN_FILE

echo "Create a Signed Statement, hashing the payload"
python /scripts/create_hashed_signed_statement.py \
  --content-type $CONTENT_TYPE \
  --issuer $ISSUER \
  --output-file "$SIGNED_STATEMENT_FILE" \
  --payload-file $PAYLOAD_FILE \
  --payload-location $PAYLOAD_LOCATION \
  --signing-key-file $SIGNING_KEY_FILE \
  --subject $SUBJECT

if [ ! -f $SIGNED_STATEMENT_FILE ]; then
  echo "ERROR: Signed Statement: [$SIGNED_STATEMENT_FILE] Not found!"
  exit 126
fi

echo "Register the SCITT Signed Statement to https://app.datatrails.ai/archivist/v1/publicscitt/entries"

python /scripts/register_signed_statement.py \
      --signed-statement-file $SIGNED_STATEMENT_FILE \
      --output-file $TRANSPARENT_STATEMENT_FILE

python /scripts/dump_cbor.py \
      --input $TRANSPARENT_STATEMENT_FILE

# curl https://app.datatrails.ai/archivist/v2/publicassets/-/events?event_attributes.subject=$SUBJECT | jq
