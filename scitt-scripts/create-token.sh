#!/bin/bash -l

set -e

# echo "token-file:           " ${1}

if [ -z "$3" ]; then
  TOKEN_FILE=$HOME/.datatrails/bearer-token.txt
  mkdir -p $HOME/.datatrails
  chmod 0700 $HOME/.datatrails
else
  TOKEN_FILE=${1}
fi

RESPONSE=$(curl -s -S https://app.datatrails.ai/archivist/iam/v1/appidp/token \
            --data-urlencode "grant_type=client_credentials" \
            --data-urlencode "client_id=$DATATRAILS_CLIENT_ID" \
            --data-urlencode "client_secret=$DATATRAILS_CLIENT_SECRET")

if [[ $RESPONSE == *"access_token"* ]]; then

  TOKEN=$(echo -n $RESPONSE | jq -r .access_token)
  echo "PWD: $PWD"
  echo "Created: $TOKEN_FILE"
  echo Authorization: Bearer $TOKEN > $TOKEN_FILE

else
  echo $RESPONSE
  exit -1
fi
