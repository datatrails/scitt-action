#!/bin/bash -l

# Uncomment for debugging
# echo "datatrails-client_id:    " ${1}
# echo "datatrails-secret:       " ${2}
# echo "subject:                 " ${3}
# echo "payload:                 " ${4}
# echo "content-type:            " ${5}
# echo "signed-statement-file:   " ${6}
# echo "receipt-file:            " ${7}
# echo "signing-key-file:        " ${8}
# echo "issuer:                  " ${9}

SIGNED_STATEMENT_FILE=./${6}
TOKEN_FILE="./bearer-token.txt"
SUBJECT=${3}

echo "Create an access token"
/scripts/create-token.sh ${1} ${2} $TOKEN_FILE

# ls -a
# echo "PWD: $PWD"

# ls -la $TOKEN_FILE

echo "Create a Signed Statement, hashing the payload"
python /scripts/create_hashed_signed_statement.py \
  --subject ${3} \
  --payload ${4} \
  --content-type ${5} \
  --output-file $SIGNED_STATEMENT_FILE \
  --signing-key-file ${8} \
  --issuer ${9}

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
