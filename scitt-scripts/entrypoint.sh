#!/bin/bash -l

echo "scitt-client_id:       " ${1}
echo "scitt-scitt-secret:    " ${2}
echo "signed-statement-file: " ${3}
echo "feed:                  " ${4}
echo "signing-key-file:      " ${5}
echo "issuer:                " ${6}
echo "output-file:           " ${7}

# echo "Create an access token"
/scripts/create-token.sh ${1} ${2}

# echo "Test permissions with the assets API"
# ./query-assets.sh

python /scripts/create_signed_statement.py \
  --payload ${3} \
  --feed ${4} \
  --signing-key-file ${5} \
  --issuer ${6} \
  --output-file ${7}

OPERATION_ID=$(curl -X POST -H ./bearer-token.txt \
                --data-binary ${3} \
                https://app.datatrails.ai/archivist/v1/publicscitt/entries \
                | jq -r .operationID)

echo $OPERATION_ID

# ENTRY_ID=$(python scitt/check_operation_status.py --operation-id $OPERATION_ID)
