#!/bin/bash -l

# Uncomment for debugging
# echo "content-type:            " ${1}
# echo "datatrails-client_id:    " ${2}
# echo "datatrails-secret:       " ${3}
# echo "issuer:                  " ${4}
# echo "subject:                 " ${5}
# echo "payload_file:             " ${6}
# echo "payload-location:        " ${7}
# echo "receipt-file:            " ${8}
# echo "signed-statement-file:   " ${9}
# echo "signing-key-file:        " ${10}
# echo "skip-receipt:            " ${11}

CONTENT_TYPE=${1}
DATATRAILS_CLIENT_ID=${2}
DATATRAILS_SECRET_ID=${3}
ISSUER=${4}
SUBJECT=${5}
PAYLOAD=${6}
PAYLOAD_LOCATION=${7}
RECEIPT_FILE=${8}
SIGNED_STATEMENT_FILE=${9}
SIGNING_KEY_FILE=${10}

TOKEN_FILE="./bearer-token.txt"


echo "Create an access token"
/scripts/create-token.sh ${DATATRAILS_CLIENT_ID} ${DATATRAILS_SECRET_ID} $TOKEN_FILE

# ls -a

# ls -la $TOKEN_FILE

echo "Create a Signed Statement, hashing the payload"
python /scripts/create_hashed_signed_statement.py \
  --subject $SUBJECT \
  --payload $PAYLOAD_FILE \
  --content-type $CONTENT_TYPE \
  --output-file $SIGNED_STATEMENT_FILE \
  --signing-key-file $SIGNING_KEY_FILE \
  --issuer $ISSUER

echo "Register the SCITT SIgned Statement to https://app.datatrails.ai/archivist/v1/publicscitt/entries"

RESPONSE=$(curl -X POST -H @$TOKEN_FILE \
                --data-binary @$SIGNED_STATEMENT_FILE \
                https://app.datatrails.ai/archivist/v1/publicscitt/entries)

echo "RESPONSE: $RESPONSE"

OPERATION_ID=$(echo $RESPONSE | jq  -r .operationID)
echo "OPERATION_ID: $OPERATION_ID"

# echo "call: /scitt-scripts/check_operation_status.py"
# python /scripts/check_operation_status.py --operation-id $OPERATION_ID --token-file-name $TOKEN_FILE

# RESPONSE=$(python /scripts/check_operation_status.py --operation-id $OPERATION_ID --token-file-name $TOKEN_FILE)
# ENTRY_ID=$(echo $RESPONSE | jq  -r .entryID)

# curl https://app.datatrails.ai/archivist/v2/publicassets/-/events?event_attributes.subject=$SUBJECT | jq
