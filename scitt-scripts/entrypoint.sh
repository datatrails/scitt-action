#!/bin/bash -l

# echo "datatrails-client_id:    " ${1}
# echo "datatrails-secret:       " ${2}
# echo "subject:                 " ${3}
# echo "payload:                 " ${4}
# echo "content-type:            " ${5}
# echo "signed-statement-file:   " ${6}
# echo "receipt-file:            " ${7}

SIGNED_STATEMENT_FILE=./${6}
TOKEN_FILE="./bearer-token.txt"
SUBJECT=${3}

# echo "Create an access token"
/scripts/create-token.sh ${1} ${2} $TOKEN_FILE

ls -a
echo "PWD: $PWD"

ls -la $TOKEN_FILE

echo "Sign statement with key protected in Software Trust Manager"

python /scripts/create_signed_statement.py \
  --subject ${3} \
  --payload-file ${4} \
  --content-type ${5} \
  --output-file $SIGNED_STATEMENT_FILE

echo "SCITT Register to https://app.datatrails.ai/archivist/v1/publicscitt/entries"

OPERATION_ID=$(curl -X POST -H @$TOKEN_FILE \
                --data-binary @$SIGNED_STATEMENT_FILE \
                https://app.datatrails.ai/archivist/v1/publicscitt/entries | jq -r .operationID)

echo "OPERATION_ID :" $OPERATION_ID

echo "call: /scripts/check_operation_status.py"
python /scripts/check_operation_status.py --operation-id $OPERATION_ID --token-file-name $TOKEN_FILE

ENTRY_ID=$(python /scripts/check_operation_status.py --operation-id $OPERATION_ID --token-file-name $TOKEN_FILE)
echo "ENTRY_ID :" $ENTRY_ID

# curl https://app.datatrails.ai/archivist/v2/publicassets/-/events?event_attributes.feed_id=$SUBJECT | jq
