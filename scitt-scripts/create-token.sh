#!/bin/bash -l

# echo "datatrails-client_id: " ${1}
# echo "datatrails-secret:    " ${2}
# echo "token-file:           " ${3}

if [ -z "$3" ]; then
  TOKEN_FILE=$HOME/.datatrails/bearer-token.txt
  mkdir -p $HOME/.datatrails
  chmod 0700 $HOME/.datatrails
else
  TOKEN_FILE=${3}
fi

RESPONSE=$(curl -s -S https://app.datatrails.ai/archivist/iam/v1/appidp/token \
            --data-urlencode "grant_type=client_credentials" \
            --data-urlencode "client_id=${1}" \
            --data-urlencode "client_secret=${2}")

if [[ $RESPONSE == *"access_token"* ]]; then
  #rm $TOKEN_FILE

  TOKEN=$(echo -n $RESPONSE | jq -r .access_token)
  echo "PWD: $PWD"
  echo "Created: $TOKEN_FILE"
  echo Authorization: Bearer $TOKEN > $TOKEN_FILE

else
  echo $RESPONSE
  exit -1
fi
