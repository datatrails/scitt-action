#!/bin/bash -l

echo "scitt-client_id:       " ${1}
echo "scitt-scitt-secret:    " ${2}
echo "feed:                  " ${3}
echo "payload:               " ${4}
echo "signed-statement-file: " ${5}
echo "receipt-file:          " ${6}
echo "signing-key-file:      " ${7}
echo "issuer:                " ${8}

# echo "Create an access token"
/scripts/create-token.sh ${1} ${2}

# echo "Test permissions with the assets API"
# ./query-assets.sh

python /scripts/create_signed_statement.py \
  --feed ${3} \
  --payload ${4} \
  --output-file ${5} \
  --signing-key-file ${7} \
  --issuer ${8}

echo "output-file: " ${7}
cat ${7}

echo "signed-statement"
cat ${5}

echo "bearer-token.txt"
cat ./bearer-token.txt

OPERATION_ID=$(curl -vv -X POST -H ./bearer-token.txt \
                --data-binary @${5} \
                https://app.datatrails.ai/archivist/v1/publicscitt/entries \
                | jq -r .operationID)

echo $OPERATION_ID

# ENTRY_ID=$(python scitt/check_operation_status.py --operation-id $OPERATION_ID)
