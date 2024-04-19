#!/bin/bash -l

# echo "datatrails-client_id:    " ${1}
# echo "datatrails-scitt-secret: " ${2}
# echo "feed:                    " ${3}
# echo "payload:                 " ${4}
# echo "content-type:            " ${5}
# echo "signed-statement-file:   " ${6}
# echo "receipt-file:            " ${7}
# echo "signing-key-file:        " ${8}
# echo "issuer:                  " ${9}

SIGNED_STATEMENT_FILE=./${6}
TOKEN_FILE="./bearer-token.txt"

# echo "Create an access token"
/scripts/create-token.sh ${1} ${2} $TOKEN_FILE

ls -a
echo "PWD: $PWD"

ls -la $TOKEN_FILE

python /scripts/create_signed_statement.py \
  --feed ${3} \
  --payload ${4} \
  --content-type ${5} \
  --output-file $SIGNED_STATEMENT_FILE \
  --signing-key-file ${8} \
  --issuer ${9}

echo "SCITT Register to https://app.datatrails.ai/archivist/v1/publicscitt/entries"

RESPONSE=$(curl -X POST -H @$TOKEN_FILE \
                --data-binary @$SIGNED_STATEMENT_FILE \
                https://app.datatrails.ai/archivist/v1/publicscitt/entries)
echo $RESPONSE

echo "OPERATION_ID :" $OPERATION_ID | jq -r .operationID

# echo "call: /scripts/check_operation_status.py"
# python /scripts/check_operation_status.py --operation-id $OPERATION_ID --token-file-name $TOKEN_FILE

# ENTRY_ID=$(python /scripts/check_operation_status.py --operation-id $OPERATION_ID --token-file-name $TOKEN_FILE)
# echo "ENTRY_ID :" $ENTRY_ID

# curl https://app.datatrails.ai/archivist/v2/publicassets/-/events?event_attributes.feed_id=$FEED | jq
