#!/bin/bash -l

# Uncomment for debugging
# echo "content-type:            " ${1}
# echo "datatrails-client_id:    " ${2}
# echo "datatrails-secret:       " ${3}
# echo "issuer:                  " ${4}
# echo "payload-file:            " ${5}
# echo "payload-location:        " ${6}
# echo "receipt-file:            " ${7}
# echo "signed-statement-file:   " ${8}
# echo "signing-key-file:        " ${9}
# echo "skip-receipt:            " ${10}
# echo "subject:                 " ${11}

CONTENT_TYPE=${1}
DATATRAILS_CLIENT_ID=${2}
DATATRAILS_SECRET_ID=${3}
ISSUER=${4}
PAYLOAD_FILE=${5}
PAYLOAD_LOCATION=${6}
RECEIPT_FILE=${7}
SIGNED_STATEMENT_FILE=${8}
SIGNING_KEY_FILE=${9}
SKIP_RECEIPT=${10}
SUBJECT=${11}

TOKEN_FILE="./bearer-token.txt"


echo "Create an access token"
/scripts/create-token.sh ${DATATRAILS_CLIENT_ID} ${DATATRAILS_SECRET_ID} $TOKEN_FILE

# ls -a

# ls -la $TOKEN_FILE

echo "Create a Signed Statement, hashing the payload"
python /scripts/create_hashed_signed_statement.py \
  --content-type $CONTENT_TYPE \
  --issuer $ISSUER \
  --output-file $SIGNED_STATEMENT_FILE \
  --payload-file $PAYLOAD_FILE \
  --payload-location $PAYLOAD_LOCATION \
  --signing-key-file $SIGNING_KEY_FILE \
  --subject $SUBJECT

if [ ! -f $SIGNED_STATEMENT_FILE ]; then
  echo "ERROR: Signed Statement: [$SIGNED_STATEMENT_FILE] Not found!"
  return 404
fi

echo "Register the SCITT SIgned Statement to https://app.datatrails.ai/archivist/v1/publicscitt/entries"

RESPONSE=$(curl -X POST -H @$TOKEN_FILE \
                --data-binary @$SIGNED_STATEMENT_FILE \
                https://app.datatrails.ai/archivist/v1/publicscitt/entries)

echo "RESPONSE: $RESPONSE"

OPERATION_ID=$(echo $RESPONSE | jq  -r .operationID)
echo "OPERATION_ID: $OPERATION_ID"

echo "skip-receipt: $SKIP_RECEIPT"

if [ -n "$SKIP_RECEIPT" ] && [ $SKIP_RECEIPT = "1" ]; then
  echo "skipping receipt retrieval"
else
  echo "Download the SCITT Receipt: $RECEIPT_FILE"
  echo "call: /scripts/check_operation_status.py"
  python /scripts/check_operation_status.py --operation-id $OPERATION_ID --token-file-name $TOKEN_FILE

  ENTRY_ID=$(python /scripts/check_operation_status.py --operation-id $OPERATION_ID --token-file-name $TOKEN_FILE)
  echo "ENTRY_ID :" $ENTRY_ID
  curl -H @$TOKEN_FILE \
    https://app.datatrails.ai/archivist/v1/publicscitt/entries/$ENTRY_ID/receipt \
    -o $RECEIPT_FILE
fi

# curl https://app.datatrails.ai/archivist/v2/publicassets/-/events?event_attributes.subject=$SUBJECT | jq
