#!/bin/bash -l

curl -s -S -X GET -H "@./bearer-token.txt" \
    https://app.datatrails.ai/archivist/v2/assets | jq -C