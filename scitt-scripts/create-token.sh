#!/bin/bash -l

# echo "scitt-client_id:       " ${1}
# echo "scitt-scitt-secret:    " ${2}

RESPONSE=$(curl -s -S https://app.datatrails.ai/archivist/iam/v1/appidp/token \
            --data-urlencode "grant_type=client_credentials" \
            --data-urlencode "client_id=${1}" \
            --data-urlencode "client_secret=${2}")

if [[ $RESPONSE == *"access_token"* ]]; then
  #rm ./bearer-token.txt

  TOKEN=$(echo -n $RESPONSE | jq -r .access_token)
  
  echo Authorization: Bearer $TOKEN > ./bearer-token.txt
  # cat ./bearer-token.txt
else
  echo $RESPONSE
  exit -1
fi
