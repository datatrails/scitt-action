#!/bin/bash -l

echo "scitt-client_id:       " ${1}
echo "scitt-scitt-secret:    " ${2}
echo "feed:                  " ${3}
echo "payload:               " ${4}
echo "signed-statement-file: " ${5}
echo "receipt-file:          " ${6}
echo "signing-key-file:      " ${7}
echo "issuer:                " ${8}

SIGNED_STATEMENT_FILE=./${5}
TOKEN_FILE="./bearer-token.txt"

echo "list files"
ls -a

echo "SIGNED_STATEMENT_FILE: $SIGNED_STATEMENT_FILE"

# echo "Create an access token"
/scripts/create-token.sh ${1} ${2} $TOKEN_FILE

echo "list files"
ls -a

# echo "Test permissions with the assets API"
./query-assets.sh $TOKEN_FILE

echo "payload:"
cat ${4}

echo "create_signed_statement.py"

python /scripts/create_signed_statement.py \
  --feed ${3} \
  --payload ${4} \
  --output-file $SIGNED_STATEMENT_FILE \
  --signing-key-file ${7} \
  --issuer ${8}

echo "after signed statement"
ls -a

echo "output-file/signed-statement: " $SIGNED_STATEMENT_FILE
ls -la $SIGNED_STATEMENT_FILE

cat $SIGNED_STATEMENT_FILE

echo "TOKEN_FILE: $TOKEN_FILE"
cat $TOKEN_FILE

echo "POST to https://app.datatrails.ai/archivist/v1/publicscitt/entries"

OPERATION_ID=$(curl -X POST -H @$TOKEN_FILE \
                --data-binary @$SIGNED_STATEMENT_FILE \
                https://app.datatrails.ai/archivist/v1/publicscitt/entries \
                | jq -r .operationID)

echo "OPERATION_ID :" $OPERATION_ID

echo "call: /scripts/check_operation_status.py"
python /scripts/check_operation_status.py --operation-id $OPERATION_ID --token-file-name $TOKEN_FILE

ENTRY_ID=$(python /scripts/check_operation_status.py --operation-id $OPERATION_ID --token-file-name $TOKEN_FILE)
echo "ENTRY_ID :" $ENTRY_ID

curl -H @$TOKEN_FILE \
  https://app.datatrails.ai/archivist/v2/publicassets/-/events?event_attributes.feed_id=$FEED | jq


#OPERATION_ID=assets_17a64af8-8161-4fd6-a8c5-88b5d5674f74_events_5b2ede30-9b2f-4c3a-ad96-1d1267cf6dae
