#!/bin/bash -l

# echo "scitt-client_id:       " ${1}
# echo "scitt-scitt-secret:    " ${2}
# echo "token-file:            " ${3}
if [ -z "$3" ]; then
  TOKEN_FILE=$HOME/.datatrails/bearer-token.txt
else
  echo ${3}
fi

mkdir -p $HOME/.datatrails
chmod 0700 $HOME/.datatrails

echo $TOKEN_FILE

RESPONSE=$(curl -s -S https://app.datatrails.ai/archivist/iam/v1/appidp/token \
            --data-urlencode "grant_type=client_credentials" \
            --data-urlencode "client_id=${1}" \
            --data-urlencode "client_secret=${2}")

if [[ $RESPONSE == *"access_token"* ]]; then
  #rm $TOKEN_FILE

  TOKEN=$(echo -n $RESPONSE | jq -r .access_token)
  
  echo Authorization: Bearer $TOKEN > $TOKEN_FILE
  # cat $TOKEN_FILE
else
  echo $RESPONSE
  exit -1
fi
