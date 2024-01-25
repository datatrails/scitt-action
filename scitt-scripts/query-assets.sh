#!/bin/bash -l

curl -s -S -X GET -H "@${1}" \
    https://app.datatrails.ai/archivist/v2/assets | jq -C