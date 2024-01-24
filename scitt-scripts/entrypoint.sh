#!/bin/bash -l

# echo "scitt-client_id:       " ${1}
# echo "scitt-scitt-secret:    " ${2}
# echo "signed-statement-file: " ${3}
# echo "feed:                  " ${4}

# echo "Create an access token"
./create-token.sh ${1} ${2}

# echo "Test permissions with the assets API"
# ./query-assets.sh

./create_signed_statement.py